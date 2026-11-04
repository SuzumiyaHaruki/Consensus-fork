package tests

import (
	"bytes"
	"context"
	"encoding/json"
	sx "example.com/syncepaxos/consensus"
	"example.com/syncepaxos/nettransport"
	"fmt"
	"net/http/httptest"
	"testing"
	"time"
)

type cmpForgeTransport struct {
	send func(context.Context, cmpPacket) error
}

func (tr cmpForgeTransport) Send(ctx context.Context, to string, m sx.Message) error {
	b, err := json.Marshal(m)
	if err != nil {
		return err
	}
	var own sx.Message
	if err = json.Unmarshal(b, &own); err != nil {
		return err
	}
	p := cmpPacket{From: own.From, To: to, Kind: own.Kind, Generation: own.Generation, Raw: own}
	if own.Command != nil {
		p.ID = own.Command.ID.Seq
	}
	for _, id := range own.Deps {
		p.Deps = append(p.Deps, id.Seq)
	}
	return tr.send(ctx, p)
}
func cmpForgeCommand(c cmpCommand) sx.Command {
	return sx.Command{Configuration: "comparison", ID: sx.ID{Client: "00000000000000000000000000000001", Seq: c.ID}, Coordinator: c.Coordinator, Operation: sx.Operation{Type: c.Kind, Key: c.Key, Value: c.Value}}
}

type cmpForgeApp struct {
	a  *cmpApp
	kv *sx.KV
}

func (a cmpForgeApp) Execute(c sx.Command) sx.Result {
	out := a.a.apply(cmpCommand{ID: c.ID.Seq}, func() cmpResult { o := a.kv.Execute(c); return cmpResult{o.Value, o.Found, o.Error} })
	return sx.Result{Value: out.Value, Found: out.Found, Error: out.Error}
}
func cmpForgeWrap(n *sx.Node) *cmpNode {
	return &cmpNode{
		submit: func(ctx context.Context, c cmpCommand) (cmpResult, error) {
			o, e := n.Submit(ctx, cmpForgeCommand(c))
			if e == nil && o.Status != "executed" {
				e = fmt.Errorf("status=%s error=%s", o.Status, o.Error)
			}
			return cmpResult{o.Result.Value, o.Result.Found, o.Result.Error}, e
		},
		receive: func(p cmpPacket) error { _, err := n.Register(p.From, p.Raw.(sx.Message)); return err },
		close:   n.Close,
		observation: func(id uint64) ([]uint64, error) {
			ctx, cancel := context.WithTimeout(context.Background(), time.Second)
			defer cancel()
			s, err := n.Snapshot(ctx)
			if err != nil {
				return nil, err
			}
			for _, r := range s.Commands {
				if r.Command.ID.Seq == id {
					out := []uint64{}
					for _, v := range r.Observation {
						out = append(out, v.Seq)
					}
					return out, nil
				}
			}
			return nil, fmt.Errorf("command missing")
		},
	}
}
func cmpMakeNode(id string, ids []string, delta time.Duration, clock *cmpClock, send func(context.Context, cmpPacket) error, app *cmpApp, observe func(cmpEvent)) (*cmpNode, error) {
	cfg := sx.Config{Configuration: "comparison", Self: id, Delta: delta}
	for _, name := range ids {
		cfg.Members = append(cfg.Members, sx.Member{ID: name})
	}
	o := sx.Options{}
	if clock != nil {
		o.Clock = clock
	}
	if observe != nil {
		o.Observe = func(e sx.Event) {
			kind := e.Type
			if kind == "confirmed_dead" {
				kind = "death"
			}
			observe(cmpEvent{Node: id, Kind: kind, Peer: e.Peer, Detail: e.Detail, ID: e.Command.Seq, At: e.At})
		}
	}
	n, err := sx.New(cfg, cmpForgeTransport{send}, cmpForgeApp{app, sx.NewKV()}, o)
	if err != nil {
		return nil, err
	}
	return cmpForgeWrap(n), nil
}
func cmpObservation(n *cmpNode, _ *cmpCluster, id uint64) ([]uint64, error) { return n.observation(id) }
func cmpTCPCluster(t *testing.T, ids []string) ([]*cmpNode, []*cmpApp, func()) {
	t.Helper()
	cfg := nettransport.ClusterConfig{Configuration: "comparison", Delta: "30s"}
	servers := make([]*httptest.Server, len(ids))
	keys := map[string][]byte{}
	for i, id := range ids {
		servers[i] = httptest.NewUnstartedServer(nil)
		cfg.Members = append(cfg.Members, sx.Member{ID: id, Address: servers[i].Listener.Addr().String()})
		keys[id] = bytes.Repeat([]byte{byte(i + 1)}, 32)
	}
	var nodes []*cmpNode
	var apps []*cmpApp
	var transports []*nettransport.HTTPTransport
	closeAll := func() {
		for _, n := range nodes {
			n.close()
		}
		for _, s := range servers {
			s.Close()
		}
		for _, tr := range transports {
			tr.Close()
		}
	}
	for i, id := range ids {
		tr, err := nettransport.New(cfg, id, keys)
		if err != nil {
			closeAll()
			t.Fatal(err)
		}
		transports = append(transports, tr)
		a := cmpNewApp()
		n, err := sx.New(cfg.NodeConfig(id), tr, cmpForgeApp{a, sx.NewKV()}, sx.Options{})
		if err != nil {
			closeAll()
			t.Fatal(err)
		}
		nodes = append(nodes, cmpForgeWrap(n))
		apps = append(apps, a)
		servers[i].Config.Handler = tr.Handler(n)
		servers[i].Start()
	}
	return nodes, apps, closeAll
}
