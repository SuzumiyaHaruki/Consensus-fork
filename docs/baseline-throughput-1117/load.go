// Fixed-rate HTTP workload for the delivered server; no consensus logic.
package main

import (
	"bytes"
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"math/rand"
	"net/http"
	"os"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

type Outcome struct {
	ID, Entry          int
	Planned, Sent, End int64
	Status, Error      string
	Instance           json.RawMessage
}

func dist(v []float64) map[string]float64 {
	if len(v) == 0 {
		return nil
	}
	sort.Float64s(v)
	sum := 0.0
	for _, x := range v {
		sum += x
	}
	p := func(q float64) float64 { return v[int(math.Ceil(q*float64(len(v))))-1] }
	return map[string]float64{"mean": sum / float64(len(v)), "p50": p(.5), "p95": p(.95), "p99": p(.99), "max": v[len(v)-1]}
}
func main() {
	addresses := flag.String("addresses", "", "comma separated HTTP addresses")
	rate := flag.Float64("rate", 800, "requests/s")
	seconds := flag.Float64("seconds", 15, "sending duration")
	timeout := flag.Float64("timeout", 15, "per-request reply timeout")
	topology := flag.String("topology", "random", "single, balanced, random")
	output := flag.String("output", ".", "output directory")
	seed := flag.Int64("seed", 17, "entry selection seed")
	payload := flag.Int("payload", 16, "value bytes")
	max := flag.Int("max-inflight", 65536, "load-generator resource cap")
	flag.Parse()
	addrs := strings.Split(*addresses, ",")
	count := int(*rate * *seconds)
	if *rate <= 0 || *seconds <= 0 || count < 1 || *addresses == "" {
		panic("invalid workload")
	}
	if err := os.MkdirAll(*output, 0755); err != nil {
		panic(err)
	}
	tr := &http.Transport{MaxIdleConns: 4096, MaxIdleConnsPerHost: 512, MaxConnsPerHost: 8192, IdleConnTimeout: 90 * time.Second}
	client := &http.Client{Transport: tr, Timeout: time.Duration(*timeout * 1e9)}
	defer tr.CloseIdleConnections()
	rows := make([]Outcome, count)
	var wg sync.WaitGroup
	slots := make(chan struct{}, *max)
	var active, peak atomic.Int64
	rng := rand.New(rand.NewSource(*seed))
	start := time.Now().Add(250 * time.Millisecond)
	end := start.Add(time.Duration(*seconds * 1e9))
	value := strings.Repeat("v", *payload)
	for i := 0; i < count; i++ {
		due := start.Add(time.Duration(float64(i) / *rate * 1e9))
		entry := 0
		if *topology == "balanced" {
			entry = i % len(addrs)
		} else if *topology == "random" {
			entry = rng.Intn(len(addrs))
		}
		rows[i] = Outcome{ID: i + 1, Entry: entry, Planned: due.UnixNano(), Status: "NOT_SENT"}
		if delay := time.Until(due); delay > 0 {
			time.Sleep(delay)
		}
		if !time.Now().Before(end) {
			continue
		}
		select {
		case slots <- struct{}{}:
		default:
			rows[i].Status = "DRIVER_LIMIT"
			continue
		}
		wg.Add(1)
		go func(i, entry int) {
			defer wg.Done()
			defer func() { <-slots }()
			r := &rows[i]
			r.Sent = time.Now().UnixNano()
			x := active.Add(1)
			for {
				old := peak.Load()
				if x <= old || peak.CompareAndSwap(old, x) {
					break
				}
			}
			defer active.Add(-1)
			body, _ := json.Marshal(map[string]any{"rid": map[string]any{"client": "throughput-load-session-1117", "seq": i + 1}, "op": "put", "key": fmt.Sprintf("load/%09d", i), "value": value})
			resp, err := client.Post("http://"+addrs[entry]+"/request", "application/json", bytes.NewReader(body))
			if err != nil {
				r.Status = "TRANSPORT_ERROR"
				r.Error = err.Error()
				r.End = time.Now().UnixNano()
				return
			}
			var reply struct {
				Status   string          `json:"status"`
				Error    string          `json:"error"`
				Instance json.RawMessage `json:"instance"`
			}
			err = json.NewDecoder(resp.Body).Decode(&reply)
			resp.Body.Close()
			r.End = time.Now().UnixNano()
			if err != nil {
				r.Status = "DECODE_ERROR"
				r.Error = err.Error()
			} else {
				r.Status = reply.Status
				r.Error = reply.Error
				r.Instance = reply.Instance
			}
		}(i, entry)
	}
	wg.Wait()
	observed := time.Now()
	counts := map[string]int{}
	errors := map[string]int{}
	ok := 0
	window := 0
	issued := 0
	var latency, lag []float64
	bins := map[int]int{}
	first, last := int64(0), int64(0)
	f, err := os.Create(*output + "/requests.csv")
	if err != nil {
		panic(err)
	}
	w := csv.NewWriter(f)
	w.Write([]string{"id", "entry", "planned_ns", "sent_ns", "reply_ns", "status", "error", "instance"})
	for _, r := range rows {
		counts[r.Status]++
		if r.Error != "" {
			errors[r.Error]++
		}
		if r.Sent > 0 {
			issued++
			lag = append(lag, float64(r.Sent-r.Planned)/1e6)
			if first == 0 || r.Sent < first {
				first = r.Sent
			}
		}
		if r.Status == "OK" {
			ok++
			latency = append(latency, float64(r.End-r.Sent)/1e6)
			if r.End <= end.UnixNano() {
				window++
			}
			bins[int(float64(r.End-start.UnixNano())/5e9)]++
			if r.End > last {
				last = r.End
			}
		}
		w.Write([]string{strconv.Itoa(r.ID), strconv.Itoa(r.Entry), strconv.FormatInt(r.Planned, 10), strconv.FormatInt(r.Sent, 10), strconv.FormatInt(r.End, 10), r.Status, r.Error, string(r.Instance)})
	}
	w.Flush()
	if w.Error() != nil {
		panic(w.Error())
	}
	f.Close()
	all := issued > 0 && ok == issued
	full := map[string]float64(nil)
	if all {
		full = dist(latency)
	}
	var batch any
	if all && last > first {
		batch = float64(ok) / (float64(last-first) / 1e9)
	}
	result := map[string]any{"target_rate": *rate, "seconds": *seconds, "timeout_seconds": *timeout, "topology": *topology, "planned": count, "issued": issued, "counts": counts, "errors": errors, "completed": ok, "all_completed": all, "planned_fulfilled": issued == count, "window_completed": window, "throughput_ops_s": float64(window) / *seconds, "actual_send_rate": float64(issued) / *seconds, "batch_throughput_ops_s": batch, "full_latency_ms": full, "completed_subset_latency_ms": dist(latency), "send_lag_ms": dist(lag), "peak_client_waiters": peak.Load(), "five_second_completions": bins, "start_ns": start.UnixNano(), "end_ns": end.UnixNano(), "observed_until_ns": observed.UnixNano(), "gomaxprocs": runtime.GOMAXPROCS(0)}
	b, _ := json.MarshalIndent(result, "", "  ")
	if err = os.WriteFile(*output+"/load.json", append(b, '\n'), 0644); err != nil {
		panic(err)
	}
	fmt.Printf("rate=%.0f throughput=%.1f issued=%d ok=%d counts=%v\n", *rate, float64(window) / *seconds, issued, ok, counts)
}
