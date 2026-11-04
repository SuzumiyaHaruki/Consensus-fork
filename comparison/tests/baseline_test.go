package tests

import (
	"context"
	"encoding/json"
	sx "example.com/syncepaxos"
	"example.com/syncepaxos/nettransport"
	"fmt"
	"net"
	"strconv"
	"strings"
	"testing"
	"time"
)

type cmpBaseClock struct{ *cmpClock }

func (c cmpBaseClock) AfterFunc(d time.Duration, fn func()) sx.Timer { return c.after(d, fn) }

type cmpBaseTransport struct {
	send func(context.Context, cmpPacket) error
}

func (tr cmpBaseTransport) Send(ctx context.Context, to string, m sx.Message) error {
	b, err := json.Marshal(m)
	if err != nil {
		return err
	}
	var own sx.Message
	if err = json.Unmarshal(b, &own); err != nil {
		return err
	}
	p := cmpPacket{From: own.From, To: to, Kind: own.Type, ID: own.Command.ID.RequestSeq, Generation: own.Generation, Raw: own}
	for _, id := range own.Dependencies {
		p.Deps = append(p.Deps, id.RequestSeq)
	}
	return tr.send(ctx, p)
}
func cmpBaseCommand(c cmpCommand) sx.Command {
	return sx.Command{Configuration: "comparison", ID: sx.ID{ClientID: [16]byte{15: 1}, RequestSeq: c.ID}, Coordinator: c.Coordinator, Operation: sx.Operation{Kind: map[string]string{"put": "Put", "get": "Get", "delete": "Delete"}[c.Kind], Key: c.Key, Value: c.Value}}
}
func cmpBaseApp(a *cmpApp) sx.Application {
	kv := sx.NewKV()
	return sx.ApplyFunc(func(c sx.Command) sx.Outcome {
		out := a.apply(cmpCommand{ID: c.ID.RequestSeq}, func() cmpResult { o := kv.Apply(c); return cmpResult{o.Value, o.Found, o.Error} })
		return sx.Outcome{Value: out.Value, Found: out.Found, Error: out.Error}
	})
}
func cmpBaseWrap(n *sx.Node) *cmpNode {
	return &cmpNode{
		submit: func(ctx context.Context, c cmpCommand) (cmpResult, error) {
			o, e := n.Submit(ctx, cmpBaseCommand(c))
			return cmpResult{o.Value, o.Found, o.Error}, e
		},
		receive: func(p cmpPacket) error { return n.Receive(p.From, p.Raw.(sx.Message)) },
		close:   func() { n.Close(); n.WaitObserved() },
	}
}
func cmpMakeNode(id string, ids []string, delta time.Duration, clock *cmpClock, send func(context.Context, cmpPacket) error, app *cmpApp, observe func(cmpEvent)) (*cmpNode, error) {
	cfg := sx.Config{ID: "comparison", Delta: delta}
	for _, name := range ids {
		cfg.Members = append(cfg.Members, sx.Member{ID: name})
	}
	o := sx.Options{}
	if clock != nil {
		o.Clock = cmpBaseClock{clock}
	}
	if observe != nil {
		o.Observer = func(e sx.Event) {
			observe(cmpEvent{Node: id, Kind: e.Kind, Peer: e.Peer, Detail: e.Detail, ID: e.ID.RequestSeq, At: e.At})
		}
	}
	n, err := sx.NewNode(id, cfg, cmpBaseTransport{send}, cmpBaseApp(app), o)
	if err != nil {
		return nil, err
	}
	return cmpBaseWrap(n), nil
}
func cmpObservation(_ *cmpNode, c *cmpCluster, id uint64) ([]uint64, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	for _, e := range c.events {
		if e.Node == "a" && e.Kind == "admitted" && e.ID == id {
			out := []uint64{}
			for _, item := range strings.Fields(strings.Trim(e.Detail, "[]")) {
				parts := strings.Split(item, "/")
				v, err := strconv.ParseUint(parts[len(parts)-1], 10, 64)
				if err != nil {
					return nil, err
				}
				out = append(out, v)
			}
			return out, nil
		}
	}
	return nil, fmt.Errorf("admitted observation event missing")
}
func cmpTCPCluster(t *testing.T, ids []string) ([]*cmpNode, []*cmpApp, func()) {
	t.Helper()
	cfg := nettransport.FileConfig{Configuration: "comparison", Delta: "30s", Relay: cmpAddress(t, "127.77.0.250")}
	for i, id := range ids {
		ip := fmt.Sprintf("127.77.0.%d", i+2)
		cfg.Members = append(cfg.Members, nettransport.Member{ID: id, Address: cmpAddress(t, ip), ClientAddress: cmpAddress(t, ip)})
	}
	core, err := cfg.Consensus()
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	relayDone := make(chan error, 1)
	go func() { relayDone <- nettransport.RunRelay(ctx, cfg) }()
	var nodes []*cmpNode
	var apps []*cmpApp
	var listeners []*nettransport.Listener
	closeAll := func() {
		for _, n := range nodes {
			n.close()
		}
		for _, l := range listeners {
			l.Close()
		}
		cancel()
		<-relayDone
	}
	// Wait only for listener availability; this connection does not simulate a protocol receipt.
	limit := time.Now().Add(time.Second)
	for {
		conn, err := net.DialTimeout("tcp", cfg.Relay, 10*time.Millisecond)
		if err == nil {
			conn.Close()
			break
		}
		if time.Now().After(limit) {
			cancel()
			t.Fatal("relay not listening")
		}
		time.Sleep(time.Millisecond)
	}
	for _, id := range ids {
		tr, err := nettransport.New(id, cfg)
		if err != nil {
			closeAll()
			t.Fatal(err)
		}
		a := cmpNewApp()
		n, err := sx.NewNode(id, core, tr, cmpBaseApp(a), sx.Options{})
		if err != nil {
			closeAll()
			t.Fatal(err)
		}
		nodes = append(nodes, cmpBaseWrap(n))
		apps = append(apps, a)
		ln, err := tr.Listen(n)
		if err != nil {
			closeAll()
			t.Fatal(err)
		}
		listeners = append(listeners, ln)
	}
	return nodes, apps, closeAll
}
