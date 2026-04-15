# Architecture

Understanding dgbit's system architecture.

<div class="grid cards" markdown>

-   :material-sitemap:{ .lg .middle } **Overview**

    ---

    High-level system architecture

    [:octicons-arrow-right-24: Overview](overview.md)

-   :material-bus:{ .lg .middle } **Service Bus**

    ---

    NNG-based inter-process communication

    [:octicons-arrow-right-24: Service Bus](service-bus.md)

-   :material-swap-horizontal:{ .lg .middle } **Data Flow**

    ---

    How data moves through the system

    [:octicons-arrow-right-24: Data Flow](data-flow.md)

</div>

## Design Principles

### Modularity
Each component is independent and can be deployed separately.

### Scalability
Workers can be scaled horizontally for increased throughput.

### Reliability
Async job processing with persistent state.

### Extensibility
Pluggable strategy system with registry pattern.
