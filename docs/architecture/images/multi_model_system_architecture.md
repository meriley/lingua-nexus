# Multi-Model Translation System Architecture Diagrams

## High-Level System Overview

```mermaid
graph TB
    subgraph "Client Applications"
        UA[🌐 Telegram Web UserScript<br/>Progressive Translation UI]
        AHK[🖱️ Windows AutoHotkey<br/>System-wide Translation]
        MOB[📱 Mobile App<br/>Future Platform]
    end
    
    subgraph "Load Balancer & Security"
        LB[⚖️ nginx Load Balancer<br/>Model-Aware Routing]
        WAF[🛡️ Web Application Firewall<br/>API Protection]
    end
    
    subgraph "Multi-Tier API Services"
        LEGACY[📡 Legacy NLLB API<br/>Port 8001 - Backward Compatible]
        MULTI[🔄 Multi-Model API<br/>Port 8003 - Model Selection]
        ADAPTIVE[⚡ Adaptive API<br/>Port 8003 - Intelligent Processing]
    end
    
    subgraph "Model Layer"
        NLLB[📚 NLLB-200 Model<br/>Fast Specialized Translation]
        AYA[🤖 Aya Expanse 8B<br/>Context-Aware LLM]
        REG[🎯 Model Registry<br/>Dynamic Loading]
    end
    
    subgraph "Processing Engine"
        CHUNK[🧩 Semantic Chunker<br/>Intelligent Segmentation]
        QA[📊 Quality Assessment<br/>Multi-Dimensional Scoring]
        OPT[🔍 Binary Search Optimizer<br/>Performance Tuning]
    end
    
    subgraph "Infrastructure"
        REDIS[⚡ Redis Cache<br/>Translation & Quality Cache]
        MONITOR[📊 Monitoring<br/>Performance & Quality Metrics]
        DOCKER[🐳 Docker Services<br/>Multi-Container Deployment]
    end
    
    UA --> LB
    AHK --> LB
    MOB --> LB
    
    LB --> WAF
    WAF --> LEGACY
    WAF --> MULTI
    WAF --> ADAPTIVE
    
    LEGACY --> REG
    MULTI --> REG
    ADAPTIVE --> REG
    
    REG --> NLLB
    REG --> AYA
    
    ADAPTIVE --> CHUNK
    ADAPTIVE --> QA
    ADAPTIVE --> OPT
    
    CHUNK --> NLLB
    CHUNK --> AYA
    
    REG --> REDIS
    QA --> REDIS
    
    LEGACY --> MONITOR
    MULTI --> MONITOR
    ADAPTIVE --> MONITOR
    
    DOCKER --> LEGACY
    DOCKER --> MULTI
    DOCKER --> ADAPTIVE
    DOCKER --> REDIS
```

## API Architecture Layers

```mermaid
graph LR
    subgraph "API Evolution"
        direction TB
        L1[Legacy NLLB API<br/>4 Endpoints<br/>Basic Translation]
        L2[Multi-Model API<br/>8 Endpoints<br/>Model Selection]
        L3[Adaptive API<br/>9 Endpoints<br/>Intelligent Processing]
        
        L1 --> L2
        L2 --> L3
    end
    
    subgraph "Capabilities Matrix"
        direction TB
        C1[✓ Basic Translation<br/>✓ Language Detection<br/>✓ Health Checks<br/>✓ Model Status]
        C2[✓ All Legacy Features<br/>✓ Model Management<br/>✓ Capability Queries<br/>✓ Performance Metrics]
        C3[✓ All Multi-Model Features<br/>✓ Semantic Chunking<br/>✓ Quality Assessment<br/>✓ Progressive Translation]
        
        L1 -.-> C1
        L2 -.-> C2
        L3 -.-> C3
    end
```

## Adaptive Translation Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant AdaptiveAPI
    participant SemanticChunker
    participant QualityAssessment
    participant ModelRegistry
    participant Cache
    participant Models
    
    Client->>AdaptiveAPI: POST /adaptive/translate
    AdaptiveAPI->>Cache: Check cache
    
    alt Cache Hit
        Cache-->>AdaptiveAPI: Cached result
        AdaptiveAPI-->>Client: Return translation
    else Cache Miss
        AdaptiveAPI->>SemanticChunker: Analyze text
        
        alt Simple Text
            SemanticChunker->>ModelRegistry: Select optimal model
            ModelRegistry->>Models: Direct translation
            Models-->>AdaptiveAPI: Result
        else Complex Text
            SemanticChunker->>SemanticChunker: Generate chunks
            
            loop For each chunk
                SemanticChunker->>ModelRegistry: Translate chunk
                ModelRegistry->>Models: Parallel processing
                Models-->>QualityAssessment: Chunk result
                QualityAssessment->>QualityAssessment: Score quality
                
                alt Quality < Threshold
                    QualityAssessment->>SemanticChunker: Request rechunking
                end
            end
            
            QualityAssessment->>AdaptiveAPI: Assembled result
        end
        
        AdaptiveAPI->>Cache: Store result
        AdaptiveAPI-->>Client: Return translation
    end
```

## Model Registry and Factory Pattern

```mermaid
classDiagram
    class ModelRegistry {
        +models: Dict[str, ModelConfig]
        +loaded_models: Dict[str, Model]
        +register_model(name, config)
        +get_model(name) Model
        +list_available_models() List
        +unload_model(name)
    }
    
    class ModelConfig {
        +model_name: str
        +model_class: Type
        +capabilities: List[str]
        +memory_requirements: str
        +optimization_settings: Dict
    }
    
    class BaseModel {
        <<abstract>>
        +translate(text, source_lang, target_lang)
        +get_capabilities() List[str]
        +health_check() bool
        +get_memory_usage() int
    }
    
    class NLLBModel {
        +model_name: str = "facebook/nllb-200-distilled-600M"
        +translate(text, source_lang, target_lang)
        +supports_language_pair(source, target) bool
    }
    
    class AyaModel {
        +model_name: str = "bartowski/aya-expanse-8b-GGUF"
        +translate(text, source_lang, target_lang)
        +generate_contextual_translation(text, context)
    }
    
    ModelRegistry --> ModelConfig
    ModelRegistry --> BaseModel
    BaseModel <|-- NLLBModel
    BaseModel <|-- AyaModel
```

## Semantic Chunking and Quality Assessment

```mermaid
graph TB
    subgraph "Text Analysis"
        INPUT[Input Text]
        ANALYZE[Text Complexity Analysis<br/>- Length assessment<br/>- Sentence boundaries<br/>- Semantic coherence]
        DECISION{Chunking Required?}
    end
    
    subgraph "Chunking Strategy"
        SEMANTIC[Semantic Chunking<br/>- Preserve meaning<br/>- Maintain context<br/>- Optimize size]
        BINARY[Binary Search Optimization<br/>- Find optimal chunk size<br/>- Quality feedback loop<br/>- Performance tuning]
    end
    
    subgraph "Quality Assessment"
        FLUENCY[Fluency Score<br/>30% weight<br/>Grammar & readability]
        ACCURACY[Accuracy Score<br/>40% weight<br/>Semantic preservation]
        CONSISTENCY[Consistency Score<br/>20% weight<br/>Term alignment]
        CONTEXT[Context Score<br/>10% weight<br/>Contextual coherence]
        COMBINED[Combined Quality Score<br/>Weighted average]
    end
    
    subgraph "Decision Engine"
        THRESHOLD{Quality > Threshold?}
        ACCEPT[Accept Translation]
        RECHUNK[Rechunk & Retry]
        ASSEMBLE[Final Assembly]
    end
    
    INPUT --> ANALYZE
    ANALYZE --> DECISION
    
    DECISION -->|Yes| SEMANTIC
    DECISION -->|No| ACCEPT
    
    SEMANTIC --> BINARY
    BINARY --> FLUENCY
    BINARY --> ACCURACY
    BINARY --> CONSISTENCY
    BINARY --> CONTEXT
    
    FLUENCY --> COMBINED
    ACCURACY --> COMBINED
    CONSISTENCY --> COMBINED
    CONTEXT --> COMBINED
    
    COMBINED --> THRESHOLD
    THRESHOLD -->|Yes| ACCEPT
    THRESHOLD -->|No| RECHUNK
    
    RECHUNK --> SEMANTIC
    ACCEPT --> ASSEMBLE
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Production Environment"
        subgraph "Edge Layer"
            CDN[☁️ CloudFlare CDN]
            WAF[🛡️ WAF Protection]
        end
        
        subgraph "Load Balancer"
            NGINX[⚖️ nginx<br/>SSL Termination<br/>Model-Aware Routing]
        end
        
        subgraph "NLLB Services - GPU Optimized"
            N1[🐳 NLLB Instance 1<br/>Port 8001<br/>Legacy API]
            N2[🐳 NLLB Instance 2<br/>Load Balancing]
        end
        
        subgraph "Aya Services - High Memory"
            A1[🐳 Aya Instance 1<br/>Port 8002<br/>32GB RAM]
            A2[🐳 Aya Instance 2<br/>GGUF Optimized]
        end
        
        subgraph "Multi-Model Services"
            M1[🐳 Multi-Model Instance 1<br/>Port 8003<br/>Full Feature Set]
            M2[🐳 Multi-Model Instance 2<br/>Adaptive Processing]
        end
        
        subgraph "Shared Infrastructure"
            REDIS_CLUSTER[🔄 Redis Cluster<br/>Distributed Cache]
            MONITORING[📊 Prometheus + Grafana<br/>Multi-Model Metrics]
            LOGGING[📝 ELK Stack<br/>Centralized Logging]
        end
    end
    
    CDN --> WAF
    WAF --> NGINX
    
    NGINX --> N1
    NGINX --> N2
    NGINX --> A1
    NGINX --> A2
    NGINX --> M1
    NGINX --> M2
    
    N1 --> REDIS_CLUSTER
    N2 --> REDIS_CLUSTER
    A1 --> REDIS_CLUSTER
    A2 --> REDIS_CLUSTER
    M1 --> REDIS_CLUSTER
    M2 --> REDIS_CLUSTER
    
    N1 --> MONITORING
    N2 --> MONITORING
    A1 --> MONITORING
    A2 --> MONITORING
    M1 --> MONITORING
    M2 --> MONITORING
    
    N1 --> LOGGING
    N2 --> LOGGING
    A1 --> LOGGING
    A2 --> LOGGING
    M1 --> LOGGING
    M2 --> LOGGING
```

## Progressive Translation Data Flow

```mermaid
graph TB
    subgraph "Client Interface"
        UI[User Interface<br/>Real-time Updates]
        SSE[Server-Sent Events<br/>Progressive Results]
    end
    
    subgraph "Adaptive Processing Pipeline"
        QUEUE[Translation Queue<br/>Chunk Management]
        PARALLEL[Parallel Processing<br/>Multiple Workers]
        ASSEMBLER[Result Assembler<br/>Progressive Output]
    end
    
    subgraph "Quality Control"
        QC[Quality Control<br/>Real-time Assessment]
        FEEDBACK[Feedback Loop<br/>Dynamic Adjustment]
    end
    
    UI --> QUEUE
    QUEUE --> PARALLEL
    
    PARALLEL --> QC
    QC --> FEEDBACK
    FEEDBACK --> PARALLEL
    
    QC --> ASSEMBLER
    ASSEMBLER --> SSE
    SSE --> UI
    
    ASSEMBLER -.->|Partial Results| SSE
    ASSEMBLER -.->|Progress Updates| SSE
    ASSEMBLER -.->|Final Result| SSE
```

## Security Architecture Layers

```mermaid
graph TB
    subgraph "External Security"
        FIREWALL[🔥 Firewall<br/>Multi-Port Protection]
        DDoS[🛡️ DDoS Protection<br/>Rate Limiting]
    end
    
    subgraph "Application Security"
        AUTH[🔐 Multi-Tier Authentication<br/>API Key + Model Access]
        VALIDATION[✅ Input Validation<br/>Content Filtering]
        RATE[⏱️ Dynamic Rate Limiting<br/>Model-Specific Limits]
    end
    
    subgraph "Transport Security"
        TLS[🔒 TLS 1.3<br/>End-to-End Encryption]
        CORS[🌐 CORS Policy<br/>API-Specific Origins]
    end
    
    subgraph "Runtime Security"
        CONTAINERS[📦 Container Isolation<br/>Resource Limits]
        USERS[👤 Service Users<br/>Least Privilege]
        AUDIT[📝 Security Audit<br/>Model Usage Tracking]
    end
    
    FIREWALL --> DDoS
    DDoS --> TLS
    TLS --> AUTH
    AUTH --> VALIDATION
    VALIDATION --> RATE
    RATE --> CONTAINERS
    CONTAINERS --> USERS
    USERS --> AUDIT
```

## Performance Scaling Strategy

```mermaid
graph LR
    subgraph "Scaling Dimensions"
        USERS[User Load<br/>1-10 → 1000+]
        REQUESTS[Request Volume<br/>1K → 100K+ daily]
        COMPLEXITY[Text Complexity<br/>Simple → Multi-document]
    end
    
    subgraph "NLLB Scaling"
        N_SMALL[Single Instance<br/>4 CPU, 4GB]
        N_MEDIUM[GPU Acceleration<br/>8 CPU, 8GB + GPU]
        N_LARGE[Multi-Instance<br/>Load Balanced]
    end
    
    subgraph "Aya Scaling"
        A_SMALL[High Memory<br/>8 CPU, 16GB]
        A_MEDIUM[GGUF Optimization<br/>16 CPU, 32GB]
        A_LARGE[Cluster Deployment<br/>Kubernetes]
    end
    
    subgraph "Adaptive Scaling"
        AD_SMALL[Basic Processing<br/>6 CPU, 8GB]
        AD_MEDIUM[Full Pipeline<br/>12 CPU, 16GB]
        AD_LARGE[Distributed Processing<br/>Multiple Workers]
    end
    
    USERS --> N_SMALL
    USERS --> A_SMALL
    USERS --> AD_SMALL
    
    REQUESTS --> N_MEDIUM
    REQUESTS --> A_MEDIUM
    REQUESTS --> AD_MEDIUM
    
    COMPLEXITY --> N_LARGE
    COMPLEXITY --> A_LARGE
    COMPLEXITY --> AD_LARGE
```