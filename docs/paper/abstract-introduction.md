# Consensus Forge: Engineering Consensus Systems with Coding Agents

## Abstract

Consensus underpins fault-tolerant replicated services, but a protocol leaves many decisions about concurrency, communication, and recovery to the implementer. Coding agents can build such services from scratch, run tests, and repair their own code. An agent can also give a protocol rule the same mistaken interpretation in its code and tests, or choose a communication strategy whose cost only becomes apparent under sustained load. We present Consensus Forge, a framework that links protocol obligations to the code that implements them and to executions that later agents can recheck as that code changes. Role-specific prompts guide generation and independent audit. A repair agent receives the reproduction and the revision it exercised, and a separate reviewer checks the fix against the original failure and related behavior. We used Forge to implement VFT EPaxos as a concurrent Go key-value service. On a seven-replica workload, the median of five run-level mean request latencies was 7.35 ms for direct autonomous generation, 1.24 ms for the initial Forge implementation, and 1.32 ms after repair. Independent audit uncovered defects that survived self-testing, including a retry mechanism that could indefinitely skip an older heartbeat. The repair restored retries for outstanding heartbeats, a behavior the reviewer checked on the revised code.

## 1. Introduction

A consensus protocol can say “broadcast to all replicas” in one line. In a running service, one worker can collect enough replies to advance while another still has messages queued for slow peers. Canceling the queued sends changes which peers receive that proposal and which votes can still arrive. Similar choices arise when timers fire, recovery competes with new requests, or a client waits for execution. A researcher implementing a new protocol must settle these questions before measurements of the service can say much about the protocol.

In our experiments, a coding agent given the design and system requirements could already produce independent replica processes, connect them over a network, submit client requests, and debug its code when tests failed. We ask how to use that engineering ability to build a faithful and efficient implementation from a supplied protocol, and how to tell whether later changes improve it.

**First, the protocol determines what an implementation must do, but leaves open how much work it takes.** The sender must reach every required peer, yet the protocol can leave connection handling, buffering, and encoding open. Even choices that put identical bytes on the wire can differ substantially in cost. In a separate diagnostic experiment on a directly generated service, two implementations used the same Protobuf encoding. Reusing the sender's objects and buffer raised mean throughput from 2,866 to 3,975 completed writes per second over 30 seconds at the same offered rate. A design note that simply justified the choice of Protobuf would explain neither result.

**Second, autonomous checking can reinforce the generator's mistakes.** Consider a test that submits a command, delays several peers, and asserts that the client eventually receives the right value. A slow path can return that value even when a cancellation error prevents the fast path from collecting votes it should have received. More repetitions of that assertion give no evidence about the missing sends. An auditor can make the converse mistake by injecting a vote directly into a handler that could never receive it in the running service.

**Third, a finding must remain useful as code changes.** A prose summary can lose the scheduling conditions that trigger a failure. A repair can make the original test pass by suppressing required work, or fix one path while breaking another that shares its cancellation or retry mechanism. Even a correct repair can increase synchronization or background work. A reviewer needs the original trigger and a way to check the other behavior affected by the change.

We present **Consensus Forge**, or **Forge**. Forge makes protocol obligations traceable across revisions. A later agent can locate the code responsible for a rule, rerun the test behind a finding, and examine what a change did to the observed behavior. The supplied protocol and service requirements remain authoritative during a run. A genuine gap in the design is recorded so that work on unaffected requirements can continue.

During generation, the agent builds complete request paths and keeps a short design document alongside the code. It identifies where a consequential choice takes effect and which observations support it. An auditor in a fresh session starts from the supplied rule, uses the design notes to locate the mechanism, and investigates it under a schedule allowed by the fault and timing model. To attribute a performance bottleneck, the auditor can hold the workload fixed and vary how one mechanism is used. The agents choose both the architecture and the experiments.

Repair begins with the finding, its assumptions, the reproduction, and the tested source revision. A repairer can reproduce the failure, challenge the diagnosis, or choose its own correction. A separate reviewer runs the revised code before marking a reported defect fixed and examines a related path that uses the changed mechanism. A lightweight Python controller retains commands, inputs, outputs, and their source versions across these handoffs. The controller checks which revision a command ran against. The reviewer judges what its assertion observed, and the retained record lets a reader revisit that judgment even when two sessions using the same model agree.

We study Forge through VFT EPaxos, a Go key-value service with real networking and timers, concurrent consensus instances, and multicore processing within each replica. Our evaluation compares direct autonomous generation, Forge's initial generated implementation, and its repaired implementation. The baseline receives the same protocol and system capability targets and can plan, test, debug, and delegate on its own. With seven replicas, two physical cores and four hardware threads per replica, and 800 independent-key writes per second distributed evenly across the replicas, all three implementations completed the workload. Across five runs per version, the median of the run-level mean client latencies was 7.35 ms for direct generation, 1.24 ms for Forge's initial version, and 1.32 ms after repair. The lower latency was already present in the initial version. The audit exposed a separate problem. Each new heartbeat could move the retry cursor past an earlier failed send, leaving that heartbeat pending indefinitely. A reviewer exercised the repaired retry logic independently. The latency cost of repair was more pronounced with one core per replica.

<!-- Evidence: docs/results/server/1116-fixed-rate/server-A.md, sections 2 and 4 (November 11 implementations, common fixed-rate workload, full replies); experiments/20261111T051255Z-sol-high-protocol-parallel-forge-1111-02-mhu_ai6o/issues.json, a000-heartbeat-retry-cursor-starvation (initial finding and executed review). The separate Protobuf comparison uses diagnostic builds of the November 18 baseline, two 30-second runs per build, 4,500 independent writes/s offered; docs/results/local/1118-baseline-03/README.md and docs/results/local/1118-baseline-03/codec/cluster.csv. -->

We make three contributions.

- **Protocol-guided autonomous construction.** We organize generation around complete execution paths and an evolving account of which code implements consequential protocol rules, while leaving architecture and implementation choices to the agent.
- **Evidence-preserving investigation and repair.** We design and implement handoffs that retain a finding's assumptions, reproduction, observations, and source version, supporting independent review of fixes and reuse of evidence when later changes affect previously checked behavior.
- **An empirical study of VFT EPaxos construction.** We compare autonomous generation with guided generation and iterative repair, characterize defects that survive self-testing, and measure both performance gains and repair costs under common workloads and resource allocations.

## 2. Background and Related Work

### 2.1 From consensus algorithms to replicated services

Consensus establishes agreement under a specified failure model. In replicated state machines, that agreement must support a compatible execution of client commands. Safety rules out forbidden outcomes, such as incompatible decisions for the same consensus instance. Liveness requires progress under stated assumptions about failures, communication, and scheduling. A client that times out has observed a delay. Deciding whether its request can ever complete requires reasoning about which replicas still hold its data and which tasks can advance it.

Protocols organize these responsibilities differently. Raft separates leader election, log replication, and safety. EPaxos allows replicas to coordinate different commands and records dependencies between interfering operations. Agreement on a command and its dependencies precedes execution, which may wait for other instances. [[1]][raft] [[2]][epaxos]

Our VFT EPaxos case study uses a supplied EPaxos-family design with fixed membership, crash-stop failures, and explicit timing assumptions. A replica can advance independent requests concurrently while it waits for data needed to execute an earlier one. Which parts of that work share a worker, a queue, or a connection is an engineering choice. Chandra et al. document comparable decisions about storage and recovery in their experience building a replicated service from Paxos. [[3]][paxos-live]

We distinguish three dimensions when examining an implementation. *Conformance* asks whether the code follows the specified protocol actions. *Correctness* asks whether executions satisfy the required agreement, execution, and progress properties under the assumed model. *Performance* measures the time and resources needed to provide that behavior. A missing required message can be a conformance defect even when a tested request completes through another path. Increased latency after a valid repair can be a cost without being a correctness failure.

### 2.2 Coding agents and systems construction

A coding agent repeatedly chooses actions, uses development tools, observes their outputs, and updates its implementation or plan. SWE-agent studies how an agent–computer interface supports repository navigation, editing, and testing. For systems construction, the input also shapes what the agent builds. SYSSPEC, for example, describes a file system's functionality, modularity, and concurrency separately and evolves the generated system through changes to those specifications. These approaches place engineering knowledge in the tools and materials that an agent can consult while it works. [[4]][swe-agent] [[5]][sysspec]

Work on distributed protocols varies both the starting artifact and the environment in which the result is judged. Das and Coyne generate implementations of Two-Phase Commit, ring election, and Raft and study how models debug them under simulated message loss, delay, and duplication. PatchyBFT starts from existing PBFT, HotStuff, and Raft code and generates alternative implementations of parts of those systems to diversify replicas. For a new consensus service, the protocol supplies the rules, but the agent must also construct the runtime and the tests that will exercise it. There is no reference service to supply missing behavior or settle how the implementation should handle a particular schedule. [[6]][protocol-testing] [[7]][patchybft]

### 2.3 Checking distributed implementations and their executions

Distributed validation must account for combinations of message order, failures, and local concurrency. IronFleet combines state-machine refinement with Hoare-style verification to prove safety and liveness properties of practical distributed implementations. MODIST explores concrete executions by interposing on actions of unmodified distributed systems and controlling their schedules. The strength of the resulting evidence depends on the property stated in a proof, or on the events a test can control and observe. [[8]][ironfleet] [[9]][modist]

That distinction matters when the implementation under test is itself generated. An agent may choose an event loop, per-instance locks, or multiple worker pools. Those choices determine where a test can intervene and what it can observe. Directly invoking a protocol transition can test its decision logic while bypassing the queues, timers, and network handling that deliver its events. Likewise, scheduling a crash does not establish that the crash occurred at the intended protocol point. Recording which handler ran and which sends had completed by then lets a reader determine what the execution demonstrates.

### 2.4 Autonomous auditing, repair, and evidence reuse

Recent auditing systems give agents information that local code inspection can miss. Agora uses specialized agents to propose and test scenarios involving multiple stages of an existing consensus implementation. SPECA derives properties from a natural-language specification and reuses them across implementations. In both settings an auditor can formulate a claim about code without having participated in writing it. [[10]][agora] [[11]][speca]

Repair introduces a further source of error. Ahmed et al. study test overfitting in repository issue resolution, where patches can pass available tests yet miss other cases, particularly when the tests themselves are generated or revised. In consensus code, a related case may be a different message type or phase served by the same worker. The client-visible result alone may give no indication that the worker stopped doing something another replica relies on. [[12]][overfitting]

Our unit of study is a generated service across revisions. It matters whether the generator delivered a behavior initially, an auditor first exposed its failure, or a later change restored it at a cost to another path. Retaining the initial implementation as well as the reproductions and revised code makes those distinctions available to the evaluation.

## References

1. Diego Ongaro and John Ousterhout. [In Search of an Understandable Consensus Algorithm][raft]. USENIX ATC, 2014.
2. Iulian Moraru, David G. Andersen, and Michael Kaminsky. [There Is More Consensus in Egalitarian Parliaments][epaxos]. SOSP, 2013.
3. Tushar D. Chandra, Robert Griesemer, and Joshua Redstone. [Paxos Made Live—An Engineering Perspective][paxos-live]. PODC, 2007.
4. John Yang et al. [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering][swe-agent]. NeurIPS, 2024.
5. Qingyuan Liu et al. [Sharpen the Spec, Cut the Code: A Case for Generative File System with SYSSPEC][sysspec]. FAST, 2026.
6. Ankush Das and Brendan Coyne. [Testing LLM-Generated Distributed Protocol Code][protocol-testing]. PAgE, 2026.
7. Arne Vogel, Christian Berger, and Rüdiger Kapitza. [PatchyBFT: Automating Diversification of Fault-Tolerant Systems using LLMs][patchybft]. arXiv:2609.18512, 2026.
8. Chris Hawblitzel et al. [IronFleet: Proving Practical Distributed Systems Correct][ironfleet]. SOSP, 2015.
9. Junfeng Yang et al. [MODIST: Transparent Model Checking of Unmodified Distributed Systems][modist]. NSDI, 2009.
10. Xiang Liu et al. [Agora: Toward Autonomous Bug Detection in Production-Level Consensus Protocols with LLM Agents][agora]. arXiv:2605.29910, 2026.
11. Masato Kamba, Hirotake Murakami, and Akiyoshi Sannai. [Beyond Code Reasoning: Specification-Anchored Auditing of Multi-Implementation Distributed Protocols][speca]. arXiv:2604.26495, 2026.
12. Toufique Ahmed, Jatin Ganhotra, Avraham Shinnar, and Martin Hirzel. [Investigating Test Overfitting on SWE-bench][overfitting]. arXiv:2511.16858v3, 2026.

[paxos-live]: https://research.google/pubs/paxos-made-live-an-engineering-perspective-2006-invited-talk/
[swe-agent]: https://arxiv.org/abs/2405.15793
[raft]: https://www.usenix.org/conference/atc14/technical-sessions/presentation/ongaro
[epaxos]: https://www.cs.cmu.edu/~dga/papers/epaxos-sosp2013.pdf
[ironfleet]: https://www.microsoft.com/en-us/research/publication/ironfleet-proving-practical-distributed-systems-correct/
[modist]: https://www.usenix.org/conference/nsdi-09/modist-transparent-model-checking-unmodified-distributed-systems
[sysspec]: https://www.usenix.org/conference/fast26/presentation/liu-qingyuan
[protocol-testing]: https://pldi26.sigplan.org/details/page-2026-papers/5/Testing-LLM-Generated-Distributed-Protocol-Code
[patchybft]: https://arxiv.org/abs/2609.18512
[agora]: https://arxiv.org/abs/2605.29910
[speca]: https://arxiv.org/abs/2604.26495
[overfitting]: https://arxiv.org/abs/2511.16858v3
