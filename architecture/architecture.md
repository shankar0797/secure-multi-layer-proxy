# Architecture Design

## 1. Objective

The objective of this project is to implement a secure multi-layer proxy architecture where external traffic, application routing, backend services and outbound Internet access are separated into different layers.

The architecture consists of:

- AWS Application Load Balancer
- Nginx Reverse Proxy
- Nginx API Gateway
- Dockerized microservices
- Private Docker network
- Squid Forward Proxy
- AWS Security Groups
- Health checks
- Application logging

---

## 2. High-Level Architecture

```text
                         INTERNET
                            |
                            |
                    External Users
                            |
                            v
                +----------------------+
                |   AWS Application    |
                |    Load Balancer     |
                |        :80           |
                +----------+-----------+
                           |
                           | TCP 8081
                           v
                +----------------------+
                |   Nginx Reverse      |
                |       Proxy          |
                |       :8081          |
                +----------+-----------+
                           |
                           | HTTP 8080
                           v
                +----------------------+
                |   Nginx API Gateway  |
                |       :8080          |
                +----------+-----------+
                           |
              +------------+-------------+
              |            |             |
              v            v             v
           /users       /orders       /payments
              |            |             |
              v            v             v
       +----------+  +----------+  +----------+
       |  User    |  |  Order   |  | Payment  |
       | Service  |  | Service  |  | Service  |
       |  :8001   |  |  :8002   |  |  :8003   |
       +----------+  +----------+  +----------+
              \            |             /
               \           |            /
                +-----------------------+
                | Docker backend-network|
                +-----------------------+
3. Forward Proxy Architecture

The Forward Proxy handles outbound Internet traffic from internal users.

                    INTERNAL USER
                          |
                          |
                          v
                +----------------+
                | Squid Forward  |
                | Proxy :3128    |
                +-------+--------+
                        |
                        |
                        v
                     INTERNET

The client explicitly sends traffic through the proxy.

Example:

curl -I -x http://localhost:3128 https://example.com

The Squid proxy records the request in its access logs.

4. External Request Flow

External application traffic follows this path:

External Client
      |
      v
AWS Application Load Balancer
      |
      v
Nginx Reverse Proxy
      |
      v
Nginx API Gateway
      |
      v
Backend Microservice

The ALB is the public entry point.

The backend services are not directly exposed to the Internet.

5. AWS Application Load Balancer

The Application Load Balancer provides the public entry point for the application.

Listener
HTTP :80
Target

The ALB forwards traffic to the EC2 instance on:

TCP :8081

where the Nginx Reverse Proxy is running.

Health Check

The ALB health check uses:

/health

Expected response:

HTTP 200
Reverse Proxy is healthy
6. Reverse Proxy Layer

The Reverse Proxy is implemented using Nginx.

Nginx Reverse Proxy
Port: 8081

Its primary responsibility is to receive traffic from the ALB and forward it to the internal API Gateway.

Traffic flow:

ALB
 |
 | HTTP :8081
 v
Reverse Proxy
 |
 | HTTP :8080
 v
API Gateway

The Reverse Proxy also adds forwarding headers:

Host
X-Real-IP
X-Forwarded-For
X-Forwarded-Proto

These headers allow downstream services to receive information about the original request.

7. API Gateway Layer

The API Gateway is implemented using Nginx.

Nginx API Gateway
Port: 8080

It provides path-based routing.

User API
/users

routes to:

user-service:8001
Order API
/orders

routes to:

order-service:8002
Payment API
/payments

routes to:

payment-service:8003

Architecture:

                  API Gateway
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
      /users       /orders    /payments
          |           |           |
          v           v           v
       User        Order       Payment
      Service      Service      Service
8. Microservices Layer

The application contains three independent services.

User Service
Container: user-service
Port: 8001
Order Service
Container: order-service
Port: 8002
Payment Service
Container: payment-service
Port: 8003

Each service is deployed as an independent Docker container.

9. Docker Network

The backend services communicate through a dedicated Docker network:

backend-network

The network provides service-to-service communication and Docker DNS-based service discovery.

Example:

docker exec api-gateway getent hosts user-service

docker exec api-gateway getent hosts order-service

docker exec api-gateway getent hosts payment-service

The API Gateway can communicate using Docker service names:

user-service:8001
order-service:8002
payment-service:8003
10. Backend Isolation

The backend services are not published using Docker host-port mappings.

For example:

docker run -d \
  --name user-service \
  --network backend-network \
  user-service:1.0

There is no:

-p 8001:8001

The same approach is used for:

order-service
payment-service

This provides an additional layer of isolation.

11. API Gateway Isolation

The API Gateway is also not published directly to the EC2 host.

It communicates internally with the Reverse Proxy through:

api-gateway:8080

This means external users cannot directly access the API Gateway port.

The intended path is:

ALB
 |
 v
Reverse Proxy
 |
 v
API Gateway
12. Security Group Architecture

The architecture uses AWS Security Groups to restrict network access.

ALB Security Group

The ALB accepts public HTTP traffic:

TCP 80
Source: 0.0.0.0/0
EC2 Security Group

The EC2 instance allows the Reverse Proxy port:

TCP 8081
Source: ALB Security Group

Therefore:

Internet
    |
    | TCP 80
    v
ALB Security Group
    |
    | TCP 8081
    v
EC2 Security Group
    |
    v
Reverse Proxy

Backend ports are not publicly exposed.

13. Security Boundaries

The architecture can be divided into security boundaries.

Public Layer
Internet
   |
   v
AWS ALB
Application Proxy Layer
ALB
 |
 v
Reverse Proxy
 |
 v
API Gateway
Private Application Layer
API Gateway
 |
 +---- User Service
 |
 +---- Order Service
 |
 +---- Payment Service

The backend services communicate through the Docker network.

14. Health Check Flow

The ALB periodically checks the Reverse Proxy.

AWS ALB
    |
    | GET /health
    v
Reverse Proxy
    |
    | HTTP 200
    v
ALB marks target healthy

During initial testing, the health check was configured against:

/

which returned:

HTTP 404

A dedicated health endpoint was then configured:

/health

which returned:

HTTP 200

The ALB target subsequently became healthy.

15. Logging Architecture

Logging is available at multiple layers.

AWS ALB
   |
   v
Reverse Proxy Logs
   |
   v
API Gateway Logs
   |
   v
Microservice Logs
Reverse Proxy
docker logs reverse-proxy
API Gateway
docker logs api-gateway
User Service
docker logs user-service
Order Service
docker logs order-service
Payment Service
docker logs payment-service
Squid
docker exec forward-proxy \
  tail -20 /var/log/squid/access.log
16. End-to-End Request Example

For the following request:

GET /users

the complete flow is:

External Client
      |
      v
AWS ALB :80
      |
      v
Reverse Proxy :8081
      |
      v
API Gateway :8080
      |
      v
User Service :8001
      |
      v
HTTP Response
      |
      v
Client

For:

GET /orders

the request is routed to:

Order Service :8002

For:

GET /payments

the request is routed to:

Payment Service :8003
17. Failure Isolation

The layered architecture makes it possible to identify failures by layer.

                Request Failure
                      |
                      v
                 Check ALB
                      |
              +-------+-------+
              |               |
           Healthy         Unhealthy
              |               |
              v               v
        Check Reverse      Check Target
           Proxy             Health
              |
              v
        Check API Gateway
              |
              v
        Check Microservice

This approach avoids troubleshooting all components simultaneously.

18. Design Principles

The architecture follows these principles:

Least Exposure

Only the required public entry point is exposed.

Layered Security

Multiple layers control traffic before it reaches the backend.

Service Isolation

Each microservice runs independently.

Network Isolation

Backend services communicate through a private Docker network.

Health Monitoring

The ALB continuously checks target health.

Observability

Each major component provides logs for troubleshooting.

Failure Testing

The architecture was tested by intentionally stopping components and validating recovery.

19. Production Architecture Improvements

For a production deployment, the following improvements could be considered:

AWS Networking
Private subnets for application workloads
NAT Gateway for outbound Internet access
Multiple Availability Zones
VPC endpoints where appropriate
Security
HTTPS/TLS
AWS WAF
AWS Secrets Manager
Least-privilege IAM
Restricted SSH access
Container image vulnerability scanning
Container Platform
ECS/Fargate or EKS
Auto Scaling
Multi-AZ deployment
Rolling deployments
Blue/green deployments
Observability
CloudWatch Logs
CloudWatch Metrics
CloudWatch Alarms
Centralized logging
Distributed tracing
Infrastructure
Terraform
CI/CD
Automated testing
Security scanning
20. Summary

The final request path is:

External User
     |
     v
AWS ALB
     |
     v
Nginx Reverse Proxy
     |
     v
Nginx API Gateway
     |
     +------> User Service
     |
     +------> Order Service
     |
     +------> Payment Service

The outbound Internet path is:

Internal User
     |
     v
Squid Forward Proxy
     |
     v
Internet

The architecture provides:

Layered traffic control
Backend isolation
API routing
Network-level access control
Health monitoring
Logging
Failure testing
Troubleshooting capability
