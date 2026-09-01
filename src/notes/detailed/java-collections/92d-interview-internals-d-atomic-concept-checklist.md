# 02 Java Collections — Interview, INTERNALS tier — the atomic concept checklist (§5.3.8)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [92c-interview-internals-c-puzzles-and-checklist.md](92c-interview-internals-c-puzzles-and-checklist.md) · Next: [93-drills-and-traps.md](93-drills-and-traps.md)

One line per concept in the whole note set, flat, sorted by subject folder and then by the order the
concept appears in that folder. Use it as a self-quiz: read a line and say the mechanism out loud in
one sentence. Any line you cannot, open the folder it belongs to.

This is the machine-readable surface of the set — downstream tooling parses it — so the format is
pinned: one bullet per concept, `- <concept name>`, no nesting, no trailing punctuation, no
parentheses, no tier markers.

## Self-test — before you start

Five questions about *using* the list, because the commonest way to waste it is to read it.

**Q1.** What counts as passing a line?

<details><summary>Answer</summary>

Saying the mechanism out loud in one sentence, without hedging and without looking. "Something to do
with resizing" is a fail. "On a resize, each entry either stays at index `j` or moves to
`j + oldCapacity`, decided by `(hash & oldCap) == 0`" is a pass. The out-loud part matters: silent
recognition is the illusion this list exists to break, and you will find lines you *thought* you knew
collapse the moment you have to produce a sentence.

</details>

**Q2.** You fail 60 of 486 lines on the first pass. What do you do next?

<details><summary>Answer</summary>

Write the 60 down and **do not re-read the whole set**. Group them by subject folder — they will
cluster, usually into two or three folders — and re-read only those files, then re-test the same 60
lines two days later. The list of failures is your syllabus from that point on. Re-reading everything
is the comfortable option and it will spend your remaining time on the 426 lines you already knew.

</details>

**Q3.** Why is the list ordered by subject folder rather than by importance?

<details><summary>Answer</summary>

Because failures cluster by folder, and the point of the list is to tell you *which file to open*. An
importance ordering would scatter every folder's concepts through the list and make the diagnostic
useless — you would know you were weak without knowing where. If you want an importance pass instead,
use the night-before order in [93c](93c-code-reading-and-schedule.md) §5.3.7.

</details>

**Q4.** Several lines are just a constant with a name, like "DEFAULT_CAPACITY of ten". Is reciting
the number enough?

<details><summary>Answer</summary>

No — every number needs its reason, because the interview follow-up is always "why?". Ten is applied
on the *first* `add`, from the defaulted empty sentinel, and it is distinguished from
`new ArrayList<>(0)` by array **identity** rather than by a flag. The numbers drill in
[93b](93b-drills.md) §5.3.1 pairs every constant with its reason for exactly this reason; a bare
number is the shape of an answer that has been memorised rather than understood.

</details>

**Q5.** A line names something you have never heard of. Is that a gap or a distraction?

<details><summary>Answer</summary>

A gap, but not necessarily an urgent one. The list is exhaustive over the set, so it includes
material that is genuinely rare in interviews — `closeDeletion`, `SALT32L`, the `CollSer` proxy. Mark
it, but triage by tier: the `HashMap`, `ArrayList`, contracts and iteration lines are asked
constantly, the `IdentityHashMap` and immutable-internals lines are what separate a strong answer
from an adequate one, and a few are pure "I read the source" signals. Fix the first group before you
touch the third.

</details>

## Atomic concept checklist

- why a collections framework exists
- array covariance versus generic invariance
- the optional-operation bargain
- Iterable as the root of iteration
- Collection as the root of element types
- Map as a sibling of Collection rather than a subtype
- the three Map views as the bridge into the Collection world
- the List contract
- the Set contract as behavioural rather than structural
- the Queue throw-versus-sentinel method pairs
- the Deque used as a stack and as a queue
- the marker interfaces RandomAccess Cloneable and Serializable
- the implementation catalogue for lists
- the implementation catalogue for sets
- the implementation catalogue for maps
- the implementation catalogue for queues and specials
- the null-policy matrix and the reason behind each ban
- the thread-safety matrix
- the ordering matrix
- undefined-but-stable versus undefined-and-randomised order
- the choosing decision tree
- Vector and why it is not a thread-safe ArrayList
- Vector growth depending on capacityIncrement
- Stack one-based search and bottom-up iteration
- Hashtable and Dictionary mechanics
- Enumeration versus Iterator and asIterator
- the release-by-release framework version history
- the three framework version traps
- the removed and deprecated list
- AbstractCollection and what it demands
- AbstractList and its quadratic iteration risk
- AbstractSequentialList
- AbstractSet and its smaller-side removeAll
- AbstractQueue and its null ban
- AbstractMap and its linear get
- extend versus delegate
- the compareTo contract
- consistent-with-equals and who violates it
- the Comparator combinators
- what reversed actually reverses
- never subtract to compare
- Collator for human-visible ordering
- a sorted collection's comparator fixed at construction
- the equals contract
- the hashCode contract
- why unequal hashes strand an entry
- the mutable-key trap
- getClass versus instanceof inside equals
- the 31 multiplier and its shift identity
- record equals and hashCode and the array-component trap
- String hashCode and its cached hash field
- hashIsZero
- engineered String collisions
- collision doubling by concatenation
- Integer and Long and Double and Boolean hashCode
- enum identity hash and its final modifier
- System identityHashCode
- collection equals across implementations
- List hashCode as an order-sensitive fold
- Set hashCode as a sum
- Map hashCode as a sum of key xor value
- the self-referential collection stack overflow
- type erasure
- why ArrayList holds an Object array
- heap pollution and SafeVarargs
- raw types
- the Integer cache
- boxing memory arithmetic
- the unboxing NullPointerException
- PECS
- why addAll takes a producer wildcard
- why a comparator takes a consumer wildcard
- the T extends Comparable super T bound
- why add is barred under an extends wildcard
- why wildcards belong in parameters and not in returns
- enhanced-for desugaring
- the Iterator state machine
- Iterator remove cost per implementation
- removeIf
- the three ways to walk a Map
- the four legal mutate-while-iterating strategies
- modCount and expectedModCount
- what counts as a structural modification
- the second-to-last-element silent skip
- snapshot iterators
- weakly consistent iterators
- the debugger-triggered ConcurrentModificationException
- why Spliterator exists
- the trySplit contract
- the eight Spliterator characteristics
- SIZED and SUBSIZED
- good splits versus bad splits
- the parallel-stream decision rule
- the shared common pool hazard
- IteratorSpliterator batch sizing
- writing your own Spliterator
- the gap JEP 431 filled
- SequencedCollection
- SequencedSet
- SequencedMap
- the sequenced retrofit map onto existing types
- reversed as a live write-through view
- addFirst on a reversed view landing at the source tail
- double reversal identity for List and LinkedHashMap
- putFirst throwing on comparator-ordered maps
- firstEntry returning an unmodifiable holder
- the asymmetric allocation cost of firstEntry and lastEntry
- putFirst inverting recency on an access-order map
- the getFirst source-compatibility break
- the master cost table
- amortised versus average versus worst case
- containsValue is always linear
- constant factors and the ArrayList LinkedList crossover
- RandomAccess as a runtime switch
- the Collections algorithm thresholds
- the object header
- the array header
- compressed oops and the 32 GB cliff
- the object alignment quantum
- boxing arithmetic
- HashMap Node at 32 bytes
- LinkedHashMap Entry at 40 bytes
- HashMap TreeNode at 56 bytes
- 69 bytes to store 8
- power-of-two table rounding and its memory cost
- per-collection empty footprints
- the map-of-empty-collections trap
- measuring with JOL
- compact object headers and Valhalla
- the heap-dump workflow
- the MAT collection queries
- diagnosing a bad hashCode versus over-allocation
- allocation profiling
- always-on collection-size guards
- DEFAULT_CAPACITY of ten
- the two empty-array sentinels and array identity as a flag
- grow delegating to ArraysSupport newLength
- SOFT_MAX_ARRAY_LENGTH
- the one-and-a-half times growth sequence
- add and add at index as one arraycopy
- fastRemove and the trailing null
- the null-split scan in indexOf
- ensureCapacity and trimToSize and clear
- removeIf as a two-pass bitset compaction
- batchRemove and its catch repair
- shiftTailOverGap
- SubList field wiring and the root modCount check
- Itr and ListItr state
- ArrayListSpliterator and late binding
- the two array-size OutOfMemoryErrors
- amortised analysis by the aggregate method
- amortised analysis by the accounting method
- amortised analysis by the potential method
- why one-and-a-half times and not two
- the golden-ratio allocator-reuse argument
- amortised does not mean predictable latency
- Node and the first and last fields
- the bidirectional shortcut in node at index
- the true worst-case hop count
- link and unlink pointer surgery
- GC-help nulling
- 24 bytes per node
- why LinkedList loses even at a mid-list insert
- its poor spliterator splits
- when LinkedList genuinely wins
- the circular-buffer invariant
- the reserved always-empty slot
- the no-arg capacity of seventeen
- the JDK 9 mask removal
- the JDK 12 capacity change
- the inc and dec and sub helpers
- the growth jump and the un-wrap slide
- null prohibition as a consequence of the free-slot sentinel
- no modCount and partial comodification detection
- ArrayDeque as a stack iterating top to bottom
- DEFAULT_INITIAL_CAPACITY of eleven
- the array-to-tree index mapping
- siftUp and its JIT-monomorphic split
- the smaller-child pick in siftDown
- heapify in linear time
- the constructor fast paths
- the removeAt moved-element return
- the forgetMeNot deque
- indexOf and contains as linear scans
- heap order is not sorted order
- mutating a priority in place
- no stability and the sequence-number fix
- max-heap and bounded top-k
- why a min-heap answers top-k
- the PriorityBlockingQueue allocation spinlock
- no decreaseKey
- the six HashMap constants as one designed set
- the overloaded threshold field
- Node and its four fields
- the cached hash
- the single xor-shift spread
- why spread at all
- tableSizeFor
- power-of-two capacity as the reason the index is a mask
- the getNode comparison order
- putVal control flow and the empty-bin fast path
- binCount and the off-by-one
- the treeifyBin capacity guard
- resize and its four jobs
- the lo and hi split and the single deciding bit
- order preservation within a bin
- the threshold-doubling guard
- the terminal maximum-capacity branch
- the Java 7 concurrent-resize cycle
- Java 8 lost and resurrected entries and torn size
- TreeNode split over the next overlay
- the three untreeify call sites
- untreeify on removal being structural rather than counted
- the TreeNode inheritance chain
- two-phase treeify
- moveRootToFront
- the putTreeVal ordering ladder
- tieBreakOrder
- the comparableClassFor reflective screen
- the Poisson justification for the load factor and the treeify threshold
- the hysteresis band
- the JDK Poisson table erratum
- hash-collision denial of service
- treeification requiring Comparable keys
- the sizing arithmetic and newHashMap
- putMapEntries pre-sizing
- removal never shrinking the table
- iteration order as table order then bin order
- a treeified bin headed by the current tree root
- the cached keySet and values and entrySet views
- the afterNode hooks as the LinkedHashMap seam
- Hashtable growth and modulo indexing
- prime capacity as folklore
- the before and after overlay
- the four allocation overrides
- linkNodeAtEnd and its JDK 8 name
- afterNodeAccess and the access-relink surface
- the eight afterNodeAccess call sites
- the provably unreachable afterNodeAccess arm
- afterNodeInsertion and removeEldestEntry
- afterNodeRemoval
- containsValue walking the chain rather than the table
- the ten-line LRU and its four bugs
- an over-bound LRU not draining
- access order making a read a structural write
- the ConcurrentModificationException a plain get can throw
- the Java 21 SequencedMap surface on LinkedHashMap
- ReversedLinkedHashMapView
- per-entry memory versus HashMap
- LinkedHashSet over the same overlay
- why Caffeine is the real cache
- the hand-built LRU over a sentinel-terminated list
- eviction updating both structures together
- the LFU frequency-bucket sketch
- LRU scan vulnerability versus LFU pollution by history
- W-TinyLFU
- the floor and ceiling and lower and higher table
- inclusive-flag range views
- time-series as-of lookup
- interval lookup
- the sliding-window rate limiter
- the five red-black invariants
- the height bound of twice log n
- Entry and its five fields
- rotateLeft and rotateRight
- the four fixAfterInsertion cases
- the four mirrored fixAfterDeletion cases
- deleteEntry and the successor swap
- successor and predecessor
- amortised constant cost per traversal step
- getEntry versus getEntryUsingComparator
- compare equals zero as key identity
- the contains and equals disagreement
- null keys and the comparator escape hatch
- buildFromSorted and its linear construction
- NavigableSubMap and inRange
- range views fencing writes only
- 40 bytes per entry
- AVL versus red-black
- the B-tree contrast
- ConcurrentSkipListMap probabilistic levels
- why lock-free is natural on a skip list and hard on a tree
- TreeSet as a TreeMap wrapper
- the PRESENT dummy
- add as put
- the dummy-boolean LinkedHashSet constructor
- every HashMap fact transferring to HashSet
- the memory cost of an unused value field
- newSetFromMap
- ConcurrentHashMap newKeySet
- CopyOnWriteArraySet breaking the set-over-map pattern
- EnumSet breaking the set-over-map pattern
- the bulk operations as set algebra
- the quadratic removeAll trap
- the AbstractSet removeAll size branch
- retainAll through a keySet view
- the mutable-element stranding bug
- disjoint
- missing symmetric difference and multiset semantics
- BitSet as a set of small integers
- length versus size versus cardinality
- the immediate-allocation surprise
- RoaringBitmap for sparse domains
- the EnumMap ordinal array
- density as a cost
- keyUniverse via SharedSecrets
- maskNull and unmaskNull
- the EnumMap entry iterator allocating a fresh entry per call
- the reused lastReturnedEntry as removal support only
- RegularEnumSet and its single long
- JumboEnumSet and its long array
- the negative shift distance mask
- bulk operations as single bitwise instructions
- the type-mismatch degradation of each bulk operation
- ordinal dependence
- why an enum-keyed HashMap is worse
- the IdentityHashMap deliberate contract violation
- the flat interleaved table with no entry objects
- the identity-hash scramble to an even index
- linear probing and nextKeyIndex
- the closeDeletion back-shift
- expectedMaxSize rather than capacity
- the one-null-slot rule
- the NULL_KEY sentinel
- the asymmetric equals against other maps
- WeakHashMap Entry extending WeakReference
- the ReferenceQueue and expungeStaleEntries
- the clearing relay and its unbounded gap
- the value-holds-key leak
- keys that never clear
- ThreadLocalMap having the same shape without a queue
- size with side effects
- Hashtable capacity eleven and its odd growth
- Properties over a ConcurrentHashMap
- stringPropertyNames as a filtered snapshot
- view versus copy versus snapshot
- subList as a live offset window
- the parent-modification ConcurrentModificationException
- subList clear as a range delete
- the subList retention leak
- the three Map views and what remove does through each
- entrySet yielding live nodes
- TreeMap range and reversed views
- Arrays asList as fixed-size rather than read-only
- the primitive-array varargs trap
- the List of fast paths and where the defensive copy is paid
- copyOf and its same-instance return
- shallow versus deep immutability
- defensive copying at API boundaries
- singletonList versus List of
- Map entry versus SimpleEntry versus Map Entry copyOf
- the stream-terminal-op mutability matrix
- the five immutability tiers
- List12 and ListN
- there is no Map2
- open addressing with an expansion factor of two as a correctness requirement
- the probe return encoding
- the MapN interleaved table
- SALT32L and REVERSE
- the salt driving iterators only
- CDS not pinning iteration order
- null hostility on queries
- the throwing mutators and the overridden interface defaults
- writeReplace to the CollSer proxy
- the immutable SubList delegating to the root
- ReverseOrderListView
- the List12 EMPTY sentinel for constant folding
- emptyList and List of having opposite mutator contracts
- what not thread-safe actually costs
- unsafe publication
- the single-mutex wrappers
- why iteration still needs your own lock
- why compound actions still race
- synchronized views sharing the outer mutex
- the ConcurrentHashMap field set
- the real sizeCtl encoding versus its stale javadoc
- spread and the reserved sign bit
- the three special node hashes
- casTabAt for an empty bin
- synchronized on a populated bin head
- get as volatile reads only
- the transfer stride arithmetic
- transferIndex claimed by CAS walking downward
- the ForwardingNode
- helpTransfer
- cooperative rather than stop-the-world resize
- striped counters and sumCount
- size as an estimate and mappingCount as the long form
- Contended and false sharing
- the TreeBin lockState
- the atomic compound methods
- recursive computeIfAbsent throwing rather than deadlocking
- the bulk forEach and search and reduce family
- parallelismThreshold
- why null keys and values are both forbidden
- Java 7 segments and why segment locking was abandoned
- Segment retained as a serialization stub
- the copy-on-write write path under a plain monitor
- addIfAbsent
- the COWIterator snapshot
- the copy-on-write cost model and its crossover
- the listener-list use case
- backpressure and the BlockingQueue surface
- the four-way throw and null and block and timeout matrix
- one lock and two conditions versus two locks with cascading signals
- the SynchronousQueue zero-capacity handoff
- SynchronousQueue rewritten over LinkedTransferQueue
- the DelayQueue leader-follower pattern
- the Michael-Scott lazy tail
- the self-linking unlink
- approximate size against constant-time isEmpty
- the LinkedTransferQueue dual queue
- ConcurrentSkipListMap two-phase deletion
- the unsafe-collection failure catalogue
- virtual threads and synchronized pinning
- the binarySearch return encoding
- the silently wrong unsorted case
- rotate by three reversals
- nCopies as one shared object
- the wrapper families
- checkedCollection as a debugging tool
- the Arrays surface underneath
- Collections sort delegating to List sort
- TimSort run detection and MIN_MERGE
- minRunLength
- the merge-stack invariants
- the de Gouw proof and the JDK stack-bound fix
- comparison method violates its general contract
- the three regions of dual-pivot quicksort
- why the object and primitive sorts differ
- adversarial input and the heapsort fallback
- stability demonstrated by a two-pass sort
- sorting a map by value
- the putIfAbsent return value
- the computeIfAbsent multimap idiom
- null results that remove entries
- merge for counters
- non-atomicity on a plain HashMap
- stream built on spliterator
- the Collectors to family
- the toMap duplicate-key and null throws
- groupingBy with downstreams
- when a stream is the wrong tool
- which collections are Serializable
- why elementData is transient
- HashMap readObject re-putting every entry
- the changed-hashCode serialization trap
- the comparator serialization requirement
- the deserialization gadget-chain link
- the four structures Guava adds
- the Eclipse Collections memory claim
- fastutil for primitives
- Caffeine as the real cache
- Agrona and JCTools
- the cost of the dependency
- MyArrayList growth and its sentinels
- the fail-fast Itr and ListItr
- the SubList view and structural equality
- the midpoint Spliterator
- MyLinkedList pointer surgery
- the true constant-time cursor insert
- MyArrayDeque circular helpers
- MyPriorityQueue sifts and heapify
- StablePriorityQueue via a stamped wrapper
- BoundedTopK on a min-heap
- MyHashMap spread and tableSizeFor
- lazy table allocation
- the seven-member extension surface
- the SortedBin simplification and its screened-Comparable guard
- the sorted-array bin trading insert cost for lookup cost
- MyHashSet on the PRESENT dummy
- MyLinkedHashMap and its before and after overlay
- the differential test against the real class
- MyTreeMap rotations and fixAfterInsertion
- MyTreeMap deleteEntry and fixAfterDeletion
- the fail-fast in-order iterator
- the hand-built LRU costing 64 bytes per entry
- the LFU frequency buckets
- a fixed-capacity ring buffer with an explicit count
- a Multimap with cleanup on empty
- a BiMap and its three-write rebind
- an IntArrayList making boxing concrete
- a checked-list guard dispatching on parameter position
- a ConcurrentModificationException harness
- CopyOnWriteList over an AtomicReference
- the CAS-retry loop a lock does not need

---

**Leaves covered:** 5.3.8 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 573
