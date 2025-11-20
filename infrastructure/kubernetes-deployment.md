# Kubernetes Deployment Specifications

## Infrastructure Overview

### Multi-Region Kubernetes Cluster Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              Global Traffic Manager (GTM)                     │
│              Route53 Geolocation Routing                      │
└────────────┬────────────────────┬────────────────────────────┘
             │                    │
    ┌────────▼────────┐  ┌────────▼────────┐  ┌──────────────┐
    │   US-EAST-1     │  │   EU-WEST-1     │  │  AP-SOUTH-1  │
    │   (Primary)     │  │   (Secondary)   │  │  (Tertiary)  │
    └────────┬────────┘  └────────┬────────┘  └──────┬───────┘
             │                    │                   │
    ┌────────▼────────┐  ┌────────▼────────┐  ┌─────▼────────┐
    │  EKS Cluster    │  │  EKS Cluster    │  │ EKS Cluster  │
    │  - 100 nodes    │  │  - 75 nodes     │  │ - 50 nodes   │
    │  - c5.4xlarge   │  │  - c5.4xlarge   │  │ - c5.4xlarge │
    └─────────────────┘  └─────────────────┘  └──────────────┘
```

## Kubernetes Cluster Specifications

### Node Pools

#### 1. Trading Engine Node Pool
```yaml
apiVersion: v1
kind: NodePool
metadata:
  name: trading-engine-pool
spec:
  instanceType: c5.4xlarge  # 16 vCPU, 32GB RAM
  minSize: 10
  maxSize: 100
  labels:
    workload: trading
    performance: ultra-high
  taints:
    - key: workload
      value: trading
      effect: NoSchedule
  nodeLabels:
    node.kubernetes.io/instance-type: c5.4xlarge
```

#### 2. Quantum Services Node Pool
```yaml
apiVersion: v1
kind: NodePool
metadata:
  name: quantum-services-pool
spec:
  instanceType: m5.2xlarge  # 8 vCPU, 32GB RAM
  minSize: 5
  maxSize: 50
  labels:
    workload: quantum
    performance: high
  taints:
    - key: workload
      value: quantum
      effect: NoSchedule
```

#### 3. General Services Node Pool
```yaml
apiVersion: v1
kind: NodePool
metadata:
  name: general-services-pool
spec:
  instanceType: m5.xlarge  # 4 vCPU, 16GB RAM
  minSize: 20
  maxSize: 200
  labels:
    workload: general
    performance: standard
```

#### 4. Database Node Pool
```yaml
apiVersion: v1
kind: NodePool
metadata:
  name: database-pool
spec:
  instanceType: r5.4xlarge  # 16 vCPU, 128GB RAM
  minSize: 3
  maxSize: 10
  labels:
    workload: database
    performance: high
  taints:
    - key: workload
      value: database
      effect: NoSchedule
  volumeSize: 500  # GB
  volumeType: io2  # High-performance SSD
```

## Service Deployments

### Trading Engine Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-engine
  namespace: trading
  labels:
    app: trading-engine
    version: v1
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2
      maxUnavailable: 1
  selector:
    matchLabels:
      app: trading-engine
  template:
    metadata:
      labels:
        app: trading-engine
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: workload
                    operator: In
                    values:
                      - trading
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values:
                      - trading-engine
              topologyKey: kubernetes.io/hostname
      containers:
        - name: trading-engine
          image: qfs/trading-engine:v1.2.3
          imagePullPolicy: Always
          ports:
            - name: grpc
              containerPort: 8080
              protocol: TCP
            - name: metrics
              containerPort: 9090
              protocol: TCP
          env:
            - name: RUST_LOG
              value: "info"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: trading-db-secret
                  key: connection-string
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: redis-secret
                  key: connection-string
            - name: KAFKA_BROKERS
              value: "kafka-0.kafka-headless:9092,kafka-1.kafka-headless:9092"
          resources:
            requests:
              memory: "4Gi"
              cpu: "2000m"
            limits:
              memory: "8Gi"
              cpu: "4000m"
          livenessProbe:
            grpc:
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            grpc:
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 2
          volumeMounts:
            - name: config
              mountPath: /etc/trading-engine
              readOnly: true
            - name: logs
              mountPath: /var/log/trading-engine
      volumes:
        - name: config
          configMap:
            name: trading-engine-config
        - name: logs
          emptyDir: {}
      tolerations:
        - key: workload
          operator: Equal
          value: trading
          effect: NoSchedule
---
apiVersion: v1
kind: Service
metadata:
  name: trading-engine
  namespace: trading
  labels:
    app: trading-engine
spec:
  type: ClusterIP
  ports:
    - name: grpc
      port: 8080
      targetPort: 8080
      protocol: TCP
  selector:
    app: trading-engine
```

### Quantum Orchestrator Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quantum-orchestrator
  namespace: quantum
spec:
  replicas: 5
  selector:
    matchLabels:
      app: quantum-orchestrator
  template:
    metadata:
      labels:
        app: quantum-orchestrator
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: workload
                    operator: In
                    values:
                      - quantum
      containers:
        - name: orchestrator
          image: qfs/quantum-orchestrator:v1.0.5
          ports:
            - containerPort: 8000
          env:
            - name: IBM_QUANTUM_TOKEN
              valueFrom:
                secretKeyRef:
                  name: quantum-secrets
                  key: ibm-token
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: quantum-secrets
                  key: aws-access-key
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: quantum-secrets
                  key: aws-secret-key
            - name: AZURE_QUANTUM_WORKSPACE_ID
              valueFrom:
                secretKeyRef:
                  name: quantum-secrets
                  key: azure-workspace-id
          resources:
            requests:
              memory: "2Gi"
              cpu: "1000m"
            limits:
              memory: "4Gi"
              cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: quantum-orchestrator
  namespace: quantum
spec:
  selector:
    app: quantum-orchestrator
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
```

### Market Data Service Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: market-data-service
  namespace: trading
spec:
  replicas: 20
  selector:
    matchLabels:
      app: market-data-service
  template:
    metadata:
      labels:
        app: market-data-service
    spec:
      containers:
        - name: market-data
          image: qfs/market-data-service:v2.1.0
          ports:
            - name: http
              containerPort: 8080
            - name: websocket
              containerPort: 8081
          env:
            - name: TIMESCALEDB_URL
              valueFrom:
                secretKeyRef:
                  name: timescale-secret
                  key: connection-string
            - name: REDIS_STREAM_URL
              valueFrom:
                secretKeyRef:
                  name: redis-secret
                  key: connection-string
          resources:
            requests:
              memory: "1Gi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
```

## Horizontal Pod Autoscaler (HPA)

### Trading Engine HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: trading-engine-hpa
  namespace: trading
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: trading-engine
  minReplicas: 10
  maxReplicas: 100
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    - type: Pods
      pods:
        metric:
          name: orders_per_second
        target:
          type: AverageValue
          averageValue: "1000"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
        - type: Pods
          value: 2
          periodSeconds: 60
      selectPolicy: Min
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 50
          periodSeconds: 15
        - type: Pods
          value: 5
          periodSeconds: 15
      selectPolicy: Max
```

## ConfigMaps

### Trading Engine Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: trading-engine-config
  namespace: trading
data:
  config.toml: |
    [server]
    host = "0.0.0.0"
    port = 8080

    [database]
    pool_size = 20
    connection_timeout = 30

    [trading]
    max_order_size = 1000000
    position_limit_check = true
    pre_trade_risk = true

    [matching]
    algorithm = "price-time-priority"
    orderbook_depth = 10000

    [performance]
    enable_metrics = true
    metrics_port = 9090
```

## Secrets Management

### Database Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: trading-db-secret
  namespace: trading
type: Opaque
stringData:
  connection-string: "postgresql://user:pass@postgres-primary:5432/trading"
  username: "trading_user"
  password: "secure_random_password_from_vault"
```

### External Secrets Operator

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: trading-db-credentials
  namespace: trading
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: trading-db-secret
    creationPolicy: Owner
  data:
    - secretKey: connection-string
      remoteRef:
        key: database/trading
        property: connection_string
    - secretKey: username
      remoteRef:
        key: database/trading
        property: username
    - secretKey: password
      remoteRef:
        key: database/trading
        property: password
```

## Service Mesh (Istio)

### Virtual Service

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: trading-engine
  namespace: trading
spec:
  hosts:
    - trading-engine
  http:
    - match:
        - headers:
            version:
              exact: v2
      route:
        - destination:
            host: trading-engine
            subset: v2
          weight: 20
        - destination:
            host: trading-engine
            subset: v1
          weight: 80
    - route:
        - destination:
            host: trading-engine
            subset: v1
```

### Destination Rule

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: trading-engine
  namespace: trading
spec:
  host: trading-engine
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 2
    loadBalancer:
      consistentHash:
        httpHeaderName: user-id
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
  subsets:
    - name: v1
      labels:
        version: v1
    - name: v2
      labels:
        version: v2
```

### Gateway

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: qfs-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 443
        name: https
        protocol: HTTPS
      tls:
        mode: SIMPLE
        credentialName: qfs-tls-cert
      hosts:
        - "api.qfs.com"
        - "*.qfs.com"
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - "*.qfs.com"
      tls:
        httpsRedirect: true
```

## Persistent Storage

### StatefulSet for Kafka

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kafka
  namespace: messaging
spec:
  serviceName: kafka-headless
  replicas: 3
  selector:
    matchLabels:
      app: kafka
  template:
    metadata:
      labels:
        app: kafka
    spec:
      containers:
        - name: kafka
          image: confluentinc/cp-kafka:7.4.0
          ports:
            - containerPort: 9092
              name: kafka
          env:
            - name: KAFKA_BROKER_ID
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: KAFKA_ZOOKEEPER_CONNECT
              value: "zookeeper:2181"
          volumeMounts:
            - name: kafka-data
              mountPath: /var/lib/kafka/data
  volumeClaimTemplates:
    - metadata:
        name: kafka-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3-encrypted
        resources:
          requests:
            storage: 500Gi
```

### Storage Classes

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID"
  iops: "16000"
  throughput: "1000"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: io2-ultra-high-performance
provisioner: ebs.csi.aws.com
parameters:
  type: io2
  encrypted: "true"
  iops: "64000"
  throughput: "4000"
volumeBindingMode: Immediate
allowVolumeExpansion: true
```

## Network Policies

### Trading Service Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: trading-engine-policy
  namespace: trading
spec:
  podSelector:
    matchLabels:
      app: trading-engine
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: api-gateway
        - podSelector:
            matchLabels:
              app: api-gateway
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: database
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - namespaceSelector:
            matchLabels:
              name: messaging
      ports:
        - protocol: TCP
          port: 9092
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
```

## Monitoring & Logging

### Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: trading-engine-metrics
  namespace: trading
spec:
  selector:
    matchLabels:
      app: trading-engine
  endpoints:
    - port: metrics
      interval: 10s
      path: /metrics
```

### Grafana Dashboard ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-trading
  namespace: monitoring
data:
  trading-dashboard.json: |
    {
      "dashboard": {
        "title": "Trading Engine Metrics",
        "panels": [
          {
            "title": "Orders per Second",
            "targets": [
              {
                "expr": "rate(orders_total[1m])"
              }
            ]
          }
        ]
      }
    }
```

## Disaster Recovery

### Velero Backup

```yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-backup
  namespace: velero
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  template:
    includedNamespaces:
      - trading
      - quantum
      - database
    snapshotVolumes: true
    ttl: 168h  # 7 days retention
    storageLocation: aws-s3-backup
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-20
