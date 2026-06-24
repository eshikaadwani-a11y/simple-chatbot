# System Design Fundamentals

## Scalability
Vertical scaling adds power to one machine (simple, limited). Horizontal scaling
adds machines behind a load balancer (scales further, needs statelessness). Keep
app servers stateless so any instance handles any request; push state to databases,
caches, and object storage.

## Caching
Caches (Redis, Memcached) cut latency and database load. Strategies: cache-aside
(lazy load on miss), write-through, write-back. Set TTLs and plan invalidation —
"there are only two hard things: cache invalidation and naming." Watch for
thundering herd and stampedes; use locks or request coalescing.

## Databases
SQL (Postgres, MySQL) gives ACID transactions and joins — best for structured,
relational data. NoSQL (document, key-value, wide-column) trades joins/consistency
for horizontal scale and flexible schemas. Scale reads with replicas; scale writes
with sharding/partitioning by a well-chosen key. Index hot query paths.

## Asynchronous processing
Message queues (RabbitMQ, SQS) and event logs (Kafka) decouple producers from
consumers, smooth spikes, and enable retries. Use them for slow or bursty work
(emails, image processing, long LLM jobs). Kafka adds durability and replay for
multiple independent consumers.

## Reliability and the CAP theorem
CAP: under a network partition you choose consistency or availability. Improve
reliability with redundancy, health checks, timeouts, retries with backoff, circuit
breakers, and graceful degradation. Track SLIs/SLOs (latency, error rate,
availability).

## Designing an API
Prefer REST for resource CRUD; consider gRPC for low-latency internal services and
WebSockets/SSE for streaming. Version your API, paginate large lists, validate
input, and rate-limit to protect downstream systems.
