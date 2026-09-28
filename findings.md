# Findings and Security Review

## 1. Overview

This document records the key technical findings identified during the implementation and testing of the Secure Multi-Layer Proxy Architecture.

The review focuses on:

- Network exposure
- Backend isolation
- Security Group configuration
- Health checks
- Logging
- Failure handling
- Production security improvements

---

# 2. Finding - Backend Port Exposure

## Observation

During the initial implementation, the backend microservices were exposed using Docker host-port mappings.

For example:

```text
-p 8001:8001

This allowed the User Service port to be published on the EC2 host.

Similar exposure existed for:

8002 - Order Service
8003 - Payment Service
Risk

Directly publishing backend service ports increases the attack surface.

A user could potentially bypass the intended architecture:

ALB
 |
 v
Reverse Proxy
 |
 v
API Gateway
 |
 v
Backend

and attempt to access a backend service directly.

Remediation

The backend services were recreated without host-port mappings.

Example:

docker run -d \
  --name user-service \
  --network backend-network \
  user-service:1.0

No host mapping such as:

-p 8001:8001

is used.

The same approach is applied to the Order and Payment services.

Result

Backend services are accessible through the Docker network but are not directly published on the EC2 host.

3. Finding - API Gateway Exposure
Observation

During development, the API Gateway was initially published using a host-port mapping.

Example:

-p 8080:8080
Risk

Publishing the API Gateway directly on the EC2 host could allow clients to bypass the Reverse Proxy.

The intended architecture is:

ALB
 |
 v
Reverse Proxy
 |
 v
API Gateway
Remediation

The API Gateway was recreated without a host-port mapping.

The Reverse Proxy communicates with the API Gateway through the Docker network:

api-gateway:8080
Result

The API Gateway is internally accessible but is not directly exposed through the EC2 host.

4. Finding - ALB Health Check
Observation

The initial ALB health check used:

/

The Reverse Proxy returned:

HTTP 404

As a result, the ALB initially considered the target unhealthy.

Root Cause

The health-check path did not correspond to a valid health endpoint.

Remediation

A dedicated health endpoint was configured:

/health

The Reverse Proxy returns:

HTTP 200
Reverse Proxy is healthy
Result

The ALB successfully detected the target as healthy.

5. Finding - Security Group Exposure
Observation

During the security review, unnecessary public application-port rules were identified on the EC2 Security Group.

Examples included application ports that were not required for public access.

Remediation

Unnecessary public application-port rules were removed.

The intended application flow is:

Internet
   |
   | TCP 80
   v
AWS ALB
   |
   | TCP 8081
   v
EC2 Security Group
   |
   v
Reverse Proxy

The EC2 Security Group allows TCP 8081 from the ALB Security Group.

Result

Application traffic must pass through the ALB before reaching the Reverse Proxy.

6. Finding - SSH Access
Observation

SSH access was available from a broad source during the lab environment.

Risk

Allowing SSH from:

0.0.0.0/0

increases the potential attack surface.

Production Recommendation

Restrict SSH access to a trusted administrative source.

Examples:

Administrator public IP
VPN
Bastion host
AWS Systems Manager Session Manager

A production Security Group should avoid unrestricted SSH access where possible.

7. Finding - Forward Proxy Access
Observation

A Squid Forward Proxy was implemented on:

3128

The proxy controls outbound Internet requests.

Configuration

The Squid configuration permits the defined Docker network:

172.18.0.0/16

and denies other sources.

Conceptually:

Allowed Network
      |
      v
Squid :3128
      |
      v
Internet

Other Sources
      |
      X
   Denied
Result

The Forward Proxy provides a controlled outbound traffic path.

8. Finding - Logging
Observation

Logging was implemented at multiple layers.

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
Forward Proxy
docker exec forward-proxy \
  tail -20 /var/log/squid/access.log
Result

Logs provide visibility into requests and failures across the architecture.

9. Finding - Failure Isolation
Observation

The architecture was tested by intentionally stopping individual components.

Tested components included:

Reverse Proxy
API Gateway
User Service
Security Group connectivity
Result

The failure of an individual layer could be identified by following the request path:

ALB
 |
 v
Reverse Proxy
 |
 v
API Gateway
 |
 v
Microservice

This provides a structured troubleshooting approach.

10. Finding - Docker Service Discovery
Observation

Backend services communicate using Docker DNS.

Example:

docker exec api-gateway getent hosts user-service
docker exec api-gateway getent hosts order-service
docker exec api-gateway getent hosts payment-service

The services are addressed using names rather than hard-coded container IP addresses.

Example:

user-service:8001
order-service:8002
payment-service:8003
Result

Service discovery remains stable even if container IP addresses change.

11. Security Architecture

The final security model is:

                         INTERNET
                            |
                            v
                    +---------------+
                    |    AWS ALB    |
                    |      :80      |
                    +-------+-------+
                            |
                            | 8081
                            v
                    +---------------+
                    | Reverse Proxy |
                    +-------+-------+
                            |
                            | 8080
                            v
                    +---------------+
                    | API Gateway   |
                    +-------+-------+
                            |
               +------------+------------+
               |            |            |
               v            v            v
             User         Order        Payment
            Service      Service       Service
               \            |            /
                \           |           /
                 +----------------------+
                 | Docker Network       |
                 +----------------------+

Only the ALB is intended to be the public application entry point.

12. Production Recommendations

The following improvements would be recommended for a production deployment.

Networking
Deploy application workloads in private subnets
Use multiple Availability Zones
Use NAT Gateway for controlled outbound Internet access
Use VPC endpoints where appropriate
Use Route 53 for DNS
Security
Enable HTTPS/TLS
Use AWS WAF
Use AWS Secrets Manager
Implement least-privilege IAM
Restrict SSH access
Use container image vulnerability scanning
Implement network segmentation
Container Platform

The lab currently uses Docker containers on EC2.

For production, the application could be deployed using:

Amazon ECS / Fargate

or:

Amazon EKS

Additional capabilities could include:

Auto Scaling
Multi-AZ deployment
Rolling deployments
Blue/green deployments
Service discovery
Observability

Production monitoring could include:

Amazon CloudWatch Logs
CloudWatch Metrics
CloudWatch Alarms
Application monitoring
Centralized logging
Distributed tracing
Alerting
Infrastructure as Code

The AWS infrastructure can be managed using:

Terraform

This would allow:

Repeatable deployments
Version-controlled infrastructure
Environment separation
Automated provisioning
Infrastructure review through Git
CI/CD

A production pipeline could include:

GitHub
   |
   v
CI/CD Pipeline
   |
   v
Build
   |
   v
Test
   |
   v
Security Scan
   |
   v
Container Image
   |
   v
Deployment
13. Lessons Learned

This project provided hands-on experience with:

AWS Application Load Balancer
AWS Security Groups
EC2 networking
Docker containers
Docker bridge networking
Docker DNS
Nginx Reverse Proxy
Nginx API Gateway
Squid Forward Proxy
FastAPI
Health checks
Application logging
Network isolation
Failure injection
Troubleshooting
Git
GitHub
SSH-based Git authentication
14. Final Technical Summary

The final architecture provides:

1. Controlled public entry point
2. Layered request processing
3. Backend service isolation
4. Private Docker networking
5. API-based routing
6. Forward proxy for outbound traffic
7. Security Group restrictions
8. Health monitoring
9. Multi-layer logging
10. Failure testing and recovery

The architecture demonstrates how multiple network and application layers can be combined to improve traffic control, isolation, observability and troubleshooting.
