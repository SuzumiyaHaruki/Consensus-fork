// Source-level codec comparison, not a consensus throughput benchmark.
package codeccompare

import (
	"bytes"
	"encoding/json"
	"epaxosproto"
	"example.com/mixepaxos/consensus"
	"io"
	"reflect"
	"state"
	"testing"
)

func original() epaxosproto.PreAccept {
	return epaxosproto.PreAccept{LeaderId: 0, Replica: 0, Instance: 12345,
		Command: []state.Command{{Op: state.PUT, K: 12345, V: 12345}},
		Seq:     1, Deps: [5]int32{-1, -1, -1, -1, -1}}
}

func candidate() consensus.Message {
	v := consensus.Value{Cmd: consensus.Command{
		RID: consensus.RID{Client: "throughput-load-session-1117", Seq: 12346},
		Op:  "put", Key: "load/000012345", Value: "vvvvvvvvvvvvvvvv"},
		D: make([]uint64, 7), Seq: 1}
	return consensus.Message{Kind: "PreAccept", From: 0, To: 1,
		X: consensus.ID{Replica: 0, Index: 12345}, Attempt: 24689,
		Phase: 1, Nonce: 24690, Init: &v}
}

func TestSizesAndRoundTrip(t *testing.T) {
	o, c := original(), candidate()
	var buf bytes.Buffer
	o.Marshal(&buf)
	var decoded epaxosproto.PreAccept
	if err := decoded.Unmarshal(bytes.NewReader(buf.Bytes())); err != nil || !reflect.DeepEqual(o, decoded) {
		t.Fatalf("original roundtrip: %v", err)
	}
	for name, m := range map[string]interface{ Marshal(io.Writer) }{
		"OriginalPreAccept":   &o,
		"OriginalFastOK":      &epaxosproto.PreAcceptOK{Instance: o.Instance},
		"OriginalCommitShort": &epaxosproto.CommitShort{Instance: o.Instance, Count: 1, Seq: 1, Deps: o.Deps},
	} {
		buf.Reset()
		m.Marshal(&buf)
		t.Logf("%s frame_bytes=%d (payload + 1 RPC byte)", name, buf.Len()+1)
	}
	r := c
	r.Kind, r.From, r.To = "PreReply", 1, 0
	r.First = &consensus.First{D: c.Init.D, Seq: 1, Fast: true}
	l := consensus.Message{Kind: "Learn", From: 0, To: 1, X: c.X, Init: c.Init, V: c.Init}
	for name, m := range map[string]consensus.Message{"BaselinePreAccept": c, "BaselinePreReply": r, "BaselineLearn": l} {
		data, err := json.Marshal(m)
		var got consensus.Message
		if err != nil {
			t.Fatal(err)
		}
		if err := json.Unmarshal(data, &got); err != nil || !reflect.DeepEqual(m, got) {
			t.Fatalf("baseline roundtrip: %v", err)
		}
		t.Logf("%s frame_bytes=%d (JSON + 4 length bytes; excludes TLS)", name, len(data)+4)
	}
}

func BenchmarkOriginalBinaryEncode(b *testing.B) {
	m := original()
	var buf bytes.Buffer
	buf.Grow(128)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		buf.Reset()
		m.Marshal(&buf)
	}
}

func BenchmarkOriginalBinaryDecode(b *testing.B) {
	m := original()
	var buf bytes.Buffer
	m.Marshal(&buf)
	r := bytes.NewReader(buf.Bytes())
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		r.Reset(buf.Bytes())
		var got epaxosproto.PreAccept
		if err := got.Unmarshal(r); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkJSON(b *testing.B) {
	for _, name := range []string{"OriginalSchema", "Baseline"} {
		var m any = original()
		if name == "Baseline" {
			m = candidate()
		}
		data, err := json.Marshal(m)
		if err != nil {
			b.Fatal(err)
		}
		b.Run(name+"Encode", func(b *testing.B) {
			b.ReportAllocs()
			for i := 0; i < b.N; i++ {
				if _, err := json.Marshal(m); err != nil {
					b.Fatal(err)
				}
			}
		})
		b.Run(name+"Decode", func(b *testing.B) {
			b.ReportAllocs()
			for i := 0; i < b.N; i++ {
				var target any
				if name == "Baseline" {
					target = new(consensus.Message)
				} else {
					target = new(epaxosproto.PreAccept)
				}
				if err := json.Unmarshal(data, target); err != nil {
					b.Fatal(err)
				}
			}
		})
	}
}
