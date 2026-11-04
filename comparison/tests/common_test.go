package tests

// These scenarios run public autonomous Nodes. The transport retains messages
// independently of senders; adapters only translate interfaces, not decisions.
import (
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"net"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"sort"
	"strings"
	"sync"
	"testing"
	"time"
)

const cmpDelta = 100 * time.Millisecond

type cmpCommand struct {
	ID                            uint64
	Coordinator, Kind, Key, Value string
}
type cmpResult struct {
	Value string
	Found bool
	Error string
}
type cmpAnswer struct {
	Result cmpResult
	Err    error
}
type cmpPacket struct {
	From, To, Kind string
	ID             uint64
	Deps           []uint64
	Generation     int
	Accepted       time.Time
	Raw            any `json:"-"`
}
type cmpEvent struct {
	Node, Kind, Peer, Detail string
	ID                       uint64
	At                       time.Time
}
type cmpNode struct {
	submit      func(context.Context, cmpCommand) (cmpResult, error)
	receive     func(cmpPacket) error
	close       func()
	observation func(uint64) ([]uint64, error)
}
type cmpTimer struct {
	clock   *cmpClock
	at      time.Time
	fn      func()
	stopped bool
}
type cmpClock struct {
	mu     sync.Mutex
	now    time.Time
	timers []*cmpTimer
}

func (c *cmpClock) Now() time.Time { c.mu.Lock(); defer c.mu.Unlock(); return c.now }
func (c *cmpClock) after(d time.Duration, fn func()) *cmpTimer {
	c.mu.Lock()
	defer c.mu.Unlock()
	t := &cmpTimer{clock: c, at: c.now.Add(d), fn: fn}
	c.timers = append(c.timers, t)
	return t
}
func (t *cmpTimer) Stop() bool {
	t.clock.mu.Lock()
	defer t.clock.mu.Unlock()
	old := t.stopped
	t.stopped = true
	return !old
}
func (c *cmpClock) After(d time.Duration) <-chan time.Time {
	ch := make(chan time.Time, 1)
	c.after(d, func() { ch <- c.Now() })
	return ch
}
func (c *cmpClock) advance(d time.Duration) {
	c.mu.Lock()
	c.now = c.now.Add(d)
	var due []func()
	var keep []*cmpTimer
	for _, timer := range c.timers {
		if timer.stopped {
			continue
		}
		if timer.at.After(c.now) {
			keep = append(keep, timer)
		} else {
			timer.stopped = true
			due = append(due, timer.fn)
		}
	}
	c.timers = keep
	c.mu.Unlock()
	for _, fn := range due {
		fn()
	}
}

type cmpApp struct {
	mu      sync.Mutex
	results map[uint64]cmpResult
	calls   map[uint64]int
	order   []uint64
	gates   map[uint64]chan struct{}
}

func cmpNewApp() *cmpApp {
	return &cmpApp{results: map[uint64]cmpResult{}, calls: map[uint64]int{}, gates: map[uint64]chan struct{}{}}
}
func (a *cmpApp) apply(c cmpCommand, realApply func() cmpResult) cmpResult {
	a.mu.Lock()
	a.calls[c.ID]++
	gate := a.gates[c.ID]
	a.mu.Unlock()
	if gate != nil {
		<-gate
	}
	out := realApply()
	a.mu.Lock()
	a.results[c.ID] = out
	a.order = append(a.order, c.ID)
	a.mu.Unlock()
	return out
}
func (a *cmpApp) done(id uint64) bool {
	a.mu.Lock()
	defer a.mu.Unlock()
	_, ok := a.results[id]
	return ok
}
func (a *cmpApp) started(id uint64) bool { a.mu.Lock(); defer a.mu.Unlock(); return a.calls[id] > 0 }
func (a *cmpApp) release(id uint64) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if ch := a.gates[id]; ch != nil {
		close(ch)
		delete(a.gates, id)
	}
}

type cmpCluster struct {
	mu            sync.Mutex
	clock         *cmpClock
	nodes         map[string]*cmpNode
	apps          map[string]*cmpApp
	dead          map[string]bool
	queue, sent   []cmpPacket
	events        []cmpEvent
	held, blocked func(cmpPacket) bool
	rng           *rand.Rand
	duplicates    bool
}

func cmpNewCluster(t *testing.T, count int, seed int64, blocked func(cmpPacket) bool) *cmpCluster {
	t.Helper()
	c := &cmpCluster{clock: &cmpClock{now: time.Unix(1000, 0)}, nodes: map[string]*cmpNode{}, apps: map[string]*cmpApp{}, dead: map[string]bool{}, rng: rand.New(rand.NewSource(seed)), blocked: blocked}
	ids := make([]string, count)
	for i := range ids {
		ids[i] = string(rune('a' + i))
	}
	for _, id := range ids {
		a := cmpNewApp()
		c.apps[id] = a
		n, err := cmpMakeNode(id, ids, cmpDelta, c.clock, c.send, a, func(e cmpEvent) { c.mu.Lock(); c.events = append(c.events, e); c.mu.Unlock() })
		if err != nil {
			t.Fatal(err)
		}
		c.nodes[id] = n
	}
	t.Cleanup(func() {
		for _, a := range c.apps {
			a.mu.Lock()
			for id, ch := range a.gates {
				close(ch)
				delete(a.gates, id)
			}
			a.mu.Unlock()
		}
		for _, id := range ids {
			c.nodes[id].close()
		}
		c.mu.Lock()
		defer c.mu.Unlock()
		data, _ := json.MarshalIndent(struct {
			Sent   []cmpPacket
			Events []cmpEvent
			Dead   map[string]bool
		}{c.sent, c.events, c.dead}, "", "  ")
		name := strings.ReplaceAll(t.Name(), "/", "-")
		_ = os.MkdirAll("comparison-traces", 0755)
		if err := os.WriteFile(filepath.Join("comparison-traces", name+".json"), data, 0644); err != nil {
			t.Error(err)
		}
		for _, e := range c.events {
			if e.Kind == "death" && !c.dead[e.Peer] {
				t.Errorf("false death: %+v", e)
			}
			if strings.Contains(e.Kind, "violation") {
				t.Errorf("reported violation: %+v", e)
			}
		}
	})
	return c
}
func (c *cmpCluster) send(ctx context.Context, p cmpPacket) error {
	if c.blocked != nil && c.blocked(p) {
		<-ctx.Done()
		return ctx.Err()
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	p.Accepted = c.clock.Now()
	c.sent = append(c.sent, p)
	c.queue = append(c.queue, p)
	if c.duplicates {
		c.queue = append(c.queue, p)
	}
	return nil
}
func (c *cmpCluster) deliver(t *testing.T) bool {
	t.Helper()
	c.mu.Lock()
	eligible := []int{}
	for i, p := range c.queue {
		if c.held == nil || !c.held(p) {
			eligible = append(eligible, i)
		}
	}
	if len(eligible) == 0 {
		c.mu.Unlock()
		return false
	}
	i := eligible[c.rng.Intn(len(eligible))]
	p := c.queue[i]
	c.queue = append(c.queue[:i], c.queue[i+1:]...)
	dead := c.dead[p.To]
	c.mu.Unlock()
	if !dead {
		if delay := c.clock.Now().Sub(p.Accepted); delay > cmpDelta {
			t.Fatalf("test transport exceeded Delta: %s %s->%s delay=%s", p.Kind, p.From, p.To, delay)
		}
		if err := c.nodes[p.To].receive(p); err != nil {
			t.Fatalf("Receive %s %s->%s: %v", p.Kind, p.From, p.To, err)
		}
		c.mu.Lock()
		c.events = append(c.events, cmpEvent{Node: p.To, Kind: "transport_deliver", Peer: p.From, Detail: p.Kind, ID: p.ID, At: c.clock.Now()})
		c.mu.Unlock()
	}
	return true
}
func (c *cmpCluster) settle(t *testing.T) {
	until := time.Now().Add(3 * time.Millisecond)
	for time.Now().Before(until) {
		if c.deliver(t) {
			until = time.Now().Add(3 * time.Millisecond)
		} else {
			runtime.Gosched()
		}
	}
}
func (c *cmpCluster) wait(t *testing.T, description string, advance bool, fn func() bool) {
	t.Helper()
	limit := time.Now().Add(6 * time.Second)
	next := time.Now().Add(10 * time.Millisecond)
	for !fn() {
		if time.Now().After(limit) {
			t.Fatalf("bounded observation expired: %s (not a universal liveness bound)", description)
		}
		if !c.deliver(t) {
			runtime.Gosched()
		}
		if advance && time.Now().After(next) {
			c.settle(t)
			c.clock.advance(cmpDelta / 8)
			next = time.Now().Add(10 * time.Millisecond)
		}
	}
}
func (c *cmpCluster) event(node, kind string, id uint64) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	for _, e := range c.events {
		if e.Node == node && e.Kind == kind && e.ID == id {
			return true
		}
	}
	return false
}
func (c *cmpCluster) packets() []cmpPacket {
	c.mu.Lock()
	defer c.mu.Unlock()
	return append([]cmpPacket(nil), c.sent...)
}
func (c *cmpCluster) submit(cmd cmpCommand) <-chan cmpAnswer {
	ch := make(chan cmpAnswer, 1)
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		out, err := c.nodes[cmd.Coordinator].submit(ctx, cmd)
		ch <- cmpAnswer{out, err}
	}()
	return ch
}
func (c *cmpCluster) crash(id string) {
	c.mu.Lock()
	c.dead[id] = true
	c.events = append(c.events, cmpEvent{Node: id, Kind: "environment_crash", At: c.clock.Now()})
	c.mu.Unlock()
	c.nodes[id].close()
}
func (c *cmpCluster) checkResults(t *testing.T, commands []cmpCommand, live []string) {
	t.Helper()
	for _, cmd := range commands {
		var expected cmpResult
		for i, id := range live {
			a := c.apps[id]
			a.mu.Lock()
			out, ok := a.results[cmd.ID]
			count := a.calls[cmd.ID]
			a.mu.Unlock()
			if !ok || count != 1 {
				t.Fatalf("%s command %d: present=%v calls=%d", id, cmd.ID, ok, count)
			}
			if i == 0 {
				expected = out
			} else if out != expected {
				t.Errorf("command %d result disagreement: %s=%+v expected=%+v", cmd.ID, id, out, expected)
			}
		}
	}
	// Compare actual DECIDE payloads; don't use either candidate's selection code as an oracle.
	decisions := map[uint64][]uint64{}
	for _, p := range c.packets() {
		if p.Kind == "DECIDE" {
			deps := append([]uint64{}, p.Deps...)
			sort.Slice(deps, func(i, j int) bool { return deps[i] < deps[j] })
			if old, ok := decisions[p.ID]; ok && !reflect.DeepEqual(old, deps) {
				t.Errorf("conflicting decisions for %d: %v vs %v", p.ID, old, deps)
			}
			decisions[p.ID] = deps
		}
	}
}
func TestComparisonConcurrent(t *testing.T) {
	for seed := int64(0); seed < 20; seed++ {
		t.Run(fmt.Sprint(seed), func(t *testing.T) {
			c := cmpNewCluster(t, 3, seed, nil)
			c.duplicates = true
			rng := rand.New(rand.NewSource(seed))
			var commands []cmpCommand
			var replies []<-chan cmpAnswer
			for j := 0; j < 18; j++ {
				cmd := cmpCommand{ID: uint64(j + 1), Coordinator: []string{"a", "b", "c"}[rng.Intn(3)], Kind: []string{"put", "get", "delete"}[rng.Intn(3)], Key: fmt.Sprint(rng.Intn(3))}
				if cmd.Kind == "put" {
					cmd.Value = fmt.Sprint(j)
				}
				commands = append(commands, cmd)
				replies = append(replies, c.submit(cmd))
			}
			c.wait(t, "all real applications complete", true, func() bool {
				for _, a := range c.apps {
					a.mu.Lock()
					n := len(a.results)
					a.mu.Unlock()
					if n != 18 {
						return false
					}
				}
				return true
			})
			for i, ch := range replies {
				var answer cmpAnswer
				c.wait(t, "client reply", true, func() bool {
					select {
					case answer = <-ch:
						return true
					default:
						return false
					}
				})
				if answer.Err != nil {
					t.Fatal(answer.Err)
				}
				a := c.apps[commands[i].Coordinator]
				a.mu.Lock()
				actual := a.results[commands[i].ID]
				a.mu.Unlock()
				if answer.Result != actual {
					t.Fatal("client result differs from actual application")
				}
			}
			c.checkResults(t, commands, []string{"a", "b", "c"})
		})
	}
}
func TestComparisonCycle(t *testing.T) {
	c := cmpNewCluster(t, 3, 71, nil)
	x := cmpCommand{10, "a", "put", "cycle", "x"}
	y := cmpCommand{20, "b", "put", "cycle", "y"}
	z := cmpCommand{1, "a", "put", "independent", "z"}
	w := cmpCommand{30, "a", "get", "cycle", ""}
	c.apps["a"].gates[x.ID] = make(chan struct{})
	c.apps["a"].gates[y.ID] = make(chan struct{})
	c.held = func(p cmpPacket) bool { return p.Kind == "OBSERVE" }
	replies := []<-chan cmpAnswer{c.submit(x), c.submit(y)}
	c.wait(t, "both initial observations", false, func() bool { return c.event("a", "admitted", x.ID) && c.event("b", "admitted", y.ID) })
	c.held = nil
	c.wait(t, "x application blocked", true, func() bool { return c.apps["a"].started(x.ID) })
	// Local application start does not imply all asynchronous DECIDE sends have run.
	c.wait(t, "actual cycle decisions sent", false, func() bool {
		edges := map[uint64]bool{}
		for _, p := range c.packets() {
			if p.Kind == "DECIDE" {
				for _, dep := range p.Deps {
					if p.ID == x.ID && dep == y.ID || p.ID == y.ID && dep == x.ID {
						edges[p.ID] = true
					}
				}
			}
		}
		return edges[x.ID] && edges[y.ID]
	})
	replies = append(replies, c.submit(z))
	c.wait(t, "independent command decided", true, func() bool { return c.event("a", "decided", z.ID) })
	c.apps["a"].release(x.ID)
	c.wait(t, "y application blocked", false, func() bool { return c.apps["a"].started(y.ID) })
	replies = append(replies, c.submit(w))
	c.wait(t, "post-retirement observation", false, func() bool { return c.event("a", "admitted", w.ID) })
	// Observe the actual immutable local observation through the adapter's public inspection.
	obs, err := cmpObservation(c.nodes["a"], c, w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(obs, []uint64{y.ID}) {
		t.Fatalf("new observation should retain y and omit locally executed x: %v", obs)
	}
	c.apps["a"].release(y.ID)
	c.wait(t, "all cycle applications complete", true, func() bool {
		for _, a := range c.apps {
			if !a.done(w.ID) || !a.done(z.ID) {
				return false
			}
		}
		return true
	})
	for _, ch := range replies {
		var ans cmpAnswer
		c.wait(t, "client reply", true, func() bool {
			select {
			case ans = <-ch:
				return true
			default:
				return false
			}
		})
		if ans.Err != nil {
			t.Fatal(ans.Err)
		}
	}
	c.apps["a"].mu.Lock()
	order := append([]uint64(nil), c.apps["a"].order...)
	c.apps["a"].mu.Unlock()
	if !reflect.DeepEqual(order, []uint64{x.ID, y.ID, z.ID, w.ID}) {
		t.Fatalf("established SCC interrupted: %v", order)
	}
	c.checkResults(t, []cmpCommand{x, y, z, w}, []string{"a", "b", "c"})
}
func TestComparisonRecovery(t *testing.T) {
	c := cmpNewCluster(t, 5, 19, func(p cmpPacket) bool { return p.From == "a" && p.Kind == "OBSERVE" && (p.To == "b" || p.To == "e") })
	c.crash("b")
	cmd := cmpCommand{900, "a", "put", "partial", "survives"}
	c.submit(cmd)
	c.wait(t, "c and d know original", false, func() bool { return c.event("c", "admitted", cmd.ID) && c.event("d", "admitted", cmd.ID) })
	if c.event("e", "admitted", cmd.ID) {
		t.Fatal("e unexpectedly knows original before crash")
	}
	c.crash("a")
	c.wait(t, "survivors recover without client retry", true, func() bool { return c.apps["c"].done(cmd.ID) && c.apps["d"].done(cmd.ID) && c.apps["e"].done(cmd.ID) })
	formal, seal := false, false
	eligible := time.Time{}
	c.mu.Lock()
	for _, e := range c.events {
		if e.Node == "c" && e.Kind == "death" && (e.Peer == "a" || e.Peer == "b") && e.At.After(eligible) {
			eligible = e.At
		}
	}
	c.mu.Unlock()
	for _, p := range c.packets() {
		if p.From == "c" && p.ID == cmd.ID {
			// READ_STATE need not carry a generation; establish eligibility from actual death events.
			if p.Kind == "READ_STATE" && p.To == "e" && !eligible.IsZero() && !p.Accepted.Before(eligible) {
				formal = true
			}
			if p.Kind == "SEAL" && p.Generation == 2 {
				seal = true
			}
		}
	}
	if !formal || !seal {
		t.Fatalf("expected successor generation 2 formal read and Seal, got read=%v seal=%v", formal, seal)
	}
	c.checkResults(t, []cmpCommand{cmd}, []string{"c", "d", "e"})
}
func TestComparisonDelta(t *testing.T) {
	// Accepting a large duration is not itself a failure: an implementation could
	// safely split long waits. If accepted, check actual behavior with three live Nodes.
	var mu sync.Mutex
	var queue []cmpPacket
	var events []cmpEvent
	nodes := map[string]*cmpNode{}
	defer func() {
		for _, n := range nodes {
			n.close()
		}
	}()
	send := func(_ context.Context, p cmpPacket) error {
		mu.Lock()
		queue = append(queue, p)
		mu.Unlock()
		return nil
	}
	observe := func(e cmpEvent) { mu.Lock(); events = append(events, e); mu.Unlock() }
	for _, id := range []string{"a", "b", "c"} {
		n, err := cmpMakeNode(id, []string{"a", "b", "c"}, time.Duration(1<<62), nil, send, cmpNewApp(), observe)
		if err != nil {
			t.Logf("rejected unrepresentable timer configuration: %v", err)
			return
		}
		nodes[id] = n
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	go func() { _, _ = nodes["a"].submit(ctx, cmpCommand{1, "a", "put", "delta", "value"}) }()
	// Ten milliseconds of actual delay is far below the accepted Delta (~146 years).
	for round := 0; round < 20; round++ {
		time.Sleep(10 * time.Millisecond)
		mu.Lock()
		packets := queue
		queue = nil
		mu.Unlock()
		for _, p := range packets {
			if err := nodes[p.To].receive(p); err != nil {
				t.Fatal(err)
			}
		}
	}
	for _, n := range nodes {
		n.close()
	}
	mu.Lock()
	defer mu.Unlock()
	for _, e := range events {
		if e.Kind == "death" {
			t.Errorf("false death of continuously live peer: node=%s peer=%s at=%s", e.Node, e.Peer, e.At)
		}
	}
}
func cmpAddress(t *testing.T, ip string) string {
	t.Helper()
	ln, err := net.Listen("tcp", ip+":0")
	if err != nil {
		t.Fatal(err)
	}
	addr := ln.Addr().String()
	ln.Close()
	return addr
}
func TestComparisonMemberIdentity(t *testing.T) {
	for _, tc := range []struct {
		name string
		ids  []string
	}{
		{"ordinary", []string{"a", "b", "c"}},
		{"newline", []string{"a\n", "b\n", "c\n"}},
		{"trailing_space", []string{"a ", "b ", "c "}},
		{"large", []string{strings.Repeat("a", 800*1024), "b", "c"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			nodes, apps, closeAll := cmpTCPCluster(t, tc.ids)
			defer closeAll()
			ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
			defer cancel()
			cmd := cmpCommand{1, tc.ids[0], "put", "identity", "value"}
			out, err := nodes[0].submit(ctx, cmd)
			if err != nil || out.Value != "value" || !out.Found {
				t.Fatalf("accepted identity cannot complete real Node/TCP command: result=%+v err=%v", out, err)
			}
			for i, a := range apps {
				for !a.done(cmd.ID) {
					select {
					case <-ctx.Done():
						t.Fatalf("replica %d did not execute", i)
					default:
						time.Sleep(time.Millisecond)
					}
				}
				a.mu.Lock()
				actual, count := a.results[cmd.ID], a.calls[cmd.ID]
				a.mu.Unlock()
				if count != 1 || actual != out {
					t.Fatalf("replica %d result=%+v count=%d", i, actual, count)
				}
			}
		})
	}
}
func TestComparisonHistory(t *testing.T) {
	// One actual Node isolates history cost from the two different production transports.
	// No observer, snapshots, network pump or race instrumentation in this measurement.
	app := cmpNewApp()
	n, err := cmpMakeNode("a", []string{"a"}, time.Hour, nil, func(context.Context, cmpPacket) error { return nil }, app, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer n.close()
	ctx, cancel := context.WithTimeout(context.Background(), 150*time.Second)
	defer cancel()
	for start := 0; start < 12000; start += 1000 {
		latencies := make([]int64, 0, 1000)
		begin := time.Now()
		for i := start; i < start+1000; i++ {
			at := time.Now()
			out, err := n.submit(ctx, cmpCommand{uint64(i + 1), "a", "put", "history", "value"})
			latencies = append(latencies, time.Since(at).Nanoseconds())
			if err != nil || out.Value != "value" {
				t.Fatalf("command %d result=%+v err=%v", i+1, out, err)
			}
		}
		elapsed := time.Since(begin)
		sort.Slice(latencies, func(i, j int) bool { return latencies[i] < latencies[j] })
		var mem runtime.MemStats
		runtime.ReadMemStats(&mem)
		t.Logf("HISTORY {\"first\":%d,\"last\":%d,\"mean_ns\":%d,\"p50_ns\":%d,\"p95_ns\":%d,\"heap_alloc\":%d}", start+1, start+1000, elapsed.Nanoseconds()/1000, latencies[500], latencies[950], mem.HeapAlloc)
	}
}
