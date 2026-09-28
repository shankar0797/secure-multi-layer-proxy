# Failure Scenarios and Troubleshooting

## 1. Purpose

This document records the failure scenarios tested against the Secure Multi-Layer Proxy Architecture.

The objective is to verify:

- Failure detection
- Troubleshooting approach
- Layer isolation
- Logging
- Recovery
- End-to-end application availability

The troubleshooting approach follows the actual traffic path:

```text
Client
  |
  v
AWS ALB
  |
  v
Reverse Proxy
  |
  v
API Gateway
  |
  v
Microservice
2. Scenario 1 - ALB Health Check Failure
Objective

Verify that an incorrect ALB health-check path causes the target to become unhealthy and that correcting the health-check endpoint restores availability.

Initial Configuration

The ALB health check was initially configured to use:

/

The Reverse Proxy did not return a successful response for this path.

The ALB therefore received:

HTTP 404
Troubleshooting

Check the Reverse Proxy logs:

docker logs reverse-proxy

The ALB health-check request was visible in the Reverse Proxy access logs.

The request showed:

GET / HTTP/1.1

with an unsuccessful HTTP response.

Root Cause

The ALB health-check path did not match a valid health endpoint in the Reverse Proxy.

Resolution

A dedicated health endpoint was configured:

/health

The Reverse Proxy returns:

HTTP 200
Reverse Proxy is healthy

The ALB health-check configuration was then changed to:

Path: /health
Success Code: 200
Verification

Check the Reverse Proxy logs:

docker logs reverse-proxy

The ALB health check should appear similar to:

GET /health HTTP/1.1
200

The ALB target subsequently became healthy.

Lesson Learned

ALB health-check paths must match a valid application or infrastructure health endpoint.

3. Scenario 2 - Reverse Proxy Failure
Objective

Verify application behavior when the Reverse Proxy is unavailable.

Failure Injection

Stop the Reverse Proxy:

docker stop reverse-proxy

Verify:

docker ps

The Reverse Proxy should no longer appear as running.

Test

Send a request through the ALB:

curl --max-time 10 http://<ALB-DNS>/users
Expected Result

The application request should fail because the ALB cannot successfully forward traffic to the Reverse Proxy.

Troubleshooting
Step 1 - Check container status
docker ps
Step 2 - Check Reverse Proxy logs
docker logs reverse-proxy
Step 3 - Check ALB target health

Check the target health in the AWS console.

Step 4 - Verify port

The Reverse Proxy should listen on:

8081
Root Cause

The Reverse Proxy container was stopped.

Recovery

Start the container:

docker start reverse-proxy

Verify:

docker ps

Then test again:

curl http://<ALB-DNS>/users
Expected Recovery

The /users endpoint should return the User Service response after the Reverse Proxy is restored.

Lesson Learned

When an application behind an ALB fails, always verify target availability and the application layer behind the target.

4. Scenario 3 - API Gateway Failure
Objective

Verify application behavior when the internal API Gateway is unavailable.

Failure Injection

Stop the API Gateway:

docker stop api-gateway

Verify:

docker ps
Test

Send a request through the ALB:

curl --max-time 10 http://<ALB-DNS>/users
Expected Result

The request should fail because the Reverse Proxy cannot successfully reach the API Gateway.

Troubleshooting

Check the API Gateway status:

docker ps

Check API Gateway logs:

docker logs api-gateway

Check Reverse Proxy logs:

docker logs reverse-proxy

The Reverse Proxy should show an upstream connection failure or unavailable upstream.

Root Cause

The API Gateway container was stopped.

Recovery

Start the API Gateway:

docker start api-gateway

Verify:

docker ps

Then test:

curl http://<ALB-DNS>/users
Expected Recovery

The User Service should become accessible again through the complete request path:

ALB
 |
 v
Reverse Proxy
 |
 v
API Gateway
 |
 v
User Service
Lesson Learned

For multi-layer architectures, troubleshooting should proceed layer by layer instead of immediately troubleshooting the backend service.

5. Scenario 4 - User Service Failure
Objective

Verify that an individual microservice failure can be isolated from other services.

Failure Injection

Stop the User Service:

docker stop user-service

Verify:

docker ps
Test User Service
curl --max-time 10 http://<ALB-DNS>/users
Expected Result

The /users request should fail because the User Service is unavailable.

Test Order Service
curl http://<ALB-DNS>/orders
Expected Result

The Order Service should continue to respond because it runs as an independent container.

Troubleshooting

Check User Service:

docker ps

Check logs:

docker logs user-service

Check API Gateway connectivity:

docker exec api-gateway getent hosts user-service
Root Cause

The User Service container was stopped.

Recovery

Start the service:

docker start user-service

Verify:

docker ps

Test again:

curl http://<ALB-DNS>/users
Expected Recovery

The User API should become available again.

Lesson Learned

Containerized microservices provide service-level isolation. Failure of one service does not necessarily mean that other services must fail.

6. Scenario 5 - Security Group Connectivity Failure
Objective

Verify the impact of removing the network rule that allows the ALB to communicate with the Reverse Proxy.

Traffic Rule

The required network path is:

ALB Security Group
        |
        | TCP 8081
        v
EC2 Security Group
        |
        v
Reverse Proxy
Failure Injection

Temporarily remove the Security Group rule allowing:

Source:
ALB Security Group

Protocol:
TCP

Port:
8081
Expected Result

The ALB should no longer be able to reach the Reverse Proxy.

The target should eventually become:

unhealthy
Troubleshooting

Check the following:

1. ALB Target Health

Verify the target status in the AWS console.

2. ALB Security Group

Verify that the ALB allows inbound HTTP traffic.

3. EC2 Security Group

Verify whether the following rule exists:

Source: ALB Security Group
Port: 8081
Protocol: TCP
4. Reverse Proxy

Verify that the container is running:

docker ps
5. Listening Port

Verify the Reverse Proxy port:

docker port reverse-proxy

Expected mapping:

8081
6. Logs

Check:

docker logs reverse-proxy
Root Cause

The ALB-to-EC2 Security Group rule was removed.

Recovery

Restore the rule:

ALB Security Group
        |
        | TCP 8081
        v
EC2 Security Group

Wait for the ALB health check to succeed.

Then test:

curl http://<ALB-DNS>/users
Expected Recovery

The ALB target should return to:

healthy

and application requests should work again.

7. Troubleshooting Decision Tree

When an application request fails:

                  Request Failure
                        |
                        v
                Check ALB Target
                     Health
                        |
             +----------+----------+
             |                     |
          Healthy               Unhealthy
             |                     |
             v                     v
     Check Reverse Proxy    Check Security Group
             |
             v
     Check API Gateway
             |
             v
     Check Microservice
             |
             v
        Check Logs
8. Standard Troubleshooting Commands
Container Status
docker ps
All Containers
docker ps -a
Container Logs
docker logs <container-name>
Docker Network
docker network inspect backend-network
DNS Resolution
docker exec api-gateway getent hosts user-service
docker exec api-gateway getent hosts order-service
docker exec api-gateway getent hosts payment-service
Reverse Proxy Port
docker port reverse-proxy
API Gateway Connectivity
docker exec reverse-proxy \
  wget -qO- http://api-gateway:8080/health
API Gateway to User Service
docker exec api-gateway \
  wget -qO- http://user-service:8001
9. Recovery Validation

After resolving any failure, validate the complete application path:

curl http://<ALB-DNS>/health

curl http://<ALB-DNS>/users

curl http://<ALB-DNS>/orders

curl http://<ALB-DNS>/payments

All endpoints should return successful responses.

10. Final Troubleshooting Approach

The troubleshooting methodology used in this project is:

1. Identify the failed request
2. Check ALB target health
3. Check Security Groups
4. Check Reverse Proxy
5. Check API Gateway
6. Check backend service
7. Inspect logs
8. Test network connectivity
9. Restore the failed component
10. Perform end-to-end validation

This approach helps isolate the failure to the correct architectural layer instead of troubleshooting the entire system at once.
