# Complete AWS Deployment Guide: 4-Node Cloud Architecture

Since your faculty permitted doing the project on AWS because you only have one Mac, this guide provides a **100% turnkey, automated deployment on AWS** within the **AWS Free Tier**.

---

## 1. Cloud Architecture Overview

Your Mac laptop acts as the **External Test Client**, while AWS hosts the 4 separate physical machine roles inside a dedicated VPC (`10.0.0.0/16`):

```
                        Your Mac Laptop (External Client)
           [dig @<DNS_IP> app.team1.test]     [curl https://app.team1.test:8443]
                                   \             /
                                    \           /
                                     v         v
==================================== AWS VPC (10.0.0.0/16) ====================================
                                Internet Gateway (IGW)
                                          |
                +-------------------------+-------------------------+
                | Public Subnet: 10.0.1.0/24                        |
                |                                                   |
                |  +-----------------------------+                  |
                |  | EC2 Instance 1 (10.0.1.10)  |                  |
                |  | Role: Private DNS Server    |                  |
                |  | Service: dnsmasq (Port 53)  |                  |
                |  | Resolves *.team1.test ->    |                  |
                |  | Edge Instance Public IP     |                  |
                |  +-----------------------------+                  |
                |                                                   |
                |  +-----------------------------+                  |
                |  | EC2 Instance 2 (10.0.1.20)  |                  |
                |  | Role: Edge Reverse Proxy/LB |                  |
                |  | Service: Nginx (Port 8443)  |                  |
                |  | TLS Termination (SSL Cert)  |                  |
                |  +--------------+--------------+                  |
                |                 | Round-Robin                     |
                |                 v Internal VPC Traffic (L4 HTTP)  |
                |        +--------+--------+                        |
                |        |                 |                        |
                |        v                 v                        |
                |  +-----------+     +-----------+                  |
                |  | EC2 Inst 3|     | EC2 Inst 4|                  |
                |  | (10.0.1.30|     | (10.0.1.40|                  |
                |  | Backend A |     | Backend B |                  |
                |  | Port 3001 |     | Port 3002 |                  |
                |  +-----------+     +-----------+                  |
==============================================================================================
```

---

## 2. Deploying to AWS (Choose Method A or Method B)

### Method A: Via AWS Web Console (Recommended & Easiest — 2 Minutes)
1. Log in to the [AWS Management Console](https://console.aws.amazon.com/).
2. Select your closest AWS Region in the top-right corner (e.g. **Asia Pacific (Mumbai) `ap-south-1`** or **US East (N. Virginia) `us-east-1`**).
3. Search for **CloudFormation** in the top search bar and open it.
4. Click **Create stack** $\rightarrow$ **With new resources (standard)**.
5. Under *Template source*, choose **Upload a template file**.
6. Click **Choose file** and select:
   `/Users/ashar/.gemini/antigravity/scratch/cn-project/aws/cloudformation.yaml`
7. Click **Next**:
   * **Stack name**: `cn-project`
   * **InstanceType**: `t2.micro` (Free Tier)
8. Click **Next** $\rightarrow$ **Next** $\rightarrow$ **Submit**.
9. Wait ~3 minutes until status changes to `CREATE_COMPLETE`.
10. Click on the **Outputs** tab to view your public IP addresses and ready-to-run commands!

---

### Method B: Via AWS CloudShell (Browser Terminal)
1. In the AWS Console, click the **CloudShell** icon ($\boxed{>\_}$) at the top bar.
2. In the terminal, upload `aws/cloudformation.yaml` (click Actions $\rightarrow$ Upload file), then run:
   ```bash
   aws cloudformation create-stack \
     --stack-name cn-project \
     --template-body file://cloudformation.yaml \
     --parameters ParameterKey=InstanceType,ParameterValue=t2.micro

   aws cloudformation wait stack-create-complete --stack-name cn-project
   ```
3. To view your outputs:
   ```bash
   aws cloudformation describe-stacks --stack-name cn-project --query "Stacks[0].Outputs" --output table
   ```

---

## 3. Testing the Entire Project from Your Mac

Replace `<DNS_PUBLIC_IP>` and `<EDGE_PUBLIC_IP>` with the values from your CloudFormation **Outputs** tab.

### Step 1: Verify DNS Resolution (Task B)
Run in your Mac's Terminal:
```bash
dig @<DNS_PUBLIC_IP> app.team1.test +short
```
* **Expected Output:** Returns your `<EDGE_PUBLIC_IP>`!

---

### Step 2: Test HTTPS & Load Balancing (Task C, D, E)
Run in your Mac's Terminal:
```bash
for i in {1..4}; do
  curl -k -i --resolve "app.team1.test:8443:<EDGE_PUBLIC_IP>" https://app.team1.test:8443/api/status | grep "X-Backend"
done
```
* **Expected Output:**
  ```
  X-Backend: A
  X-Backend: B
  X-Backend: A
  X-Backend: B
  ```
* Proves that Nginx is terminating TLS on port 8443 and round-robin load-balancing between Backend A (`10.0.1.30:3001`) and Backend B (`10.0.1.40:3002`)!

---

### Step 3: Test HTTP Caching & 304 Not Modified (Task F)
1. **Inspect headers:**
   ```bash
   curl -k -I --resolve "app.team1.test:8443:<EDGE_PUBLIC_IP>" https://app.team1.test:8443/api/status
   ```
   * Shows `Cache-Control: max-age=60` and `ETag: "backend-a-v1"`.
2. **Conditional GET:**
   ```bash
   curl -k -i --resolve "app.team1.test:8443:<EDGE_PUBLIC_IP>" -H 'If-None-Match: "backend-a-v1"' https://app.team1.test:8443/api/status | head -n 5
   ```
   * Shows `HTTP/1.1 304 Not Modified`.

---

### Step 4: Wireshark Packet Capture Evidence (Task G)
1. Open **Wireshark** on your Mac.
2. Select your active Wi-Fi interface (usually **`en0`** or **`Wi-Fi`**).
3. Filter by:
   ```
   ip.addr == <DNS_PUBLIC_IP> or ip.addr == <EDGE_PUBLIC_IP>
   ```
4. Run your `dig` and `curl` commands.
5. In Wireshark, you capture:
   * **DNS Query/Response:** Client Mac $\leftrightarrow$ `<DNS_PUBLIC_IP>:53`
   * **TCP 3-Way Handshake:** Client Mac $\leftrightarrow$ `<EDGE_PUBLIC_IP>:8443` (SYN, SYN-ACK, ACK)
   * **TLS Handshake:** ClientHello, ServerHello, Certificate, Key Exchange
   * **Encrypted Application Data:** Encrypted TLS payloads on port 8443.

---

### Step 5: Live Failure Demonstration for the Evaluator
To demonstrate **Backend Failover (Section 6.3 & Extension D)**:
1. In the AWS EC2 Console, select **`Mac3-Backend-A`**.
2. Click **Instance state** $\rightarrow$ **Stop instance**.
3. In your Mac terminal, run the curl command:
   ```bash
   curl -k -i --resolve "app.team1.test:8443:<EDGE_PUBLIC_IP>" https://app.team1.test:8443/api/status | grep "X-Backend"
   ```
   * Traffic is automatically served 100% by Backend B (`X-Backend: B`) with zero dropped requests!
4. Restart Backend A: `Instance state` $\rightarrow$ `Start instance`.
   * Round-robin balancing automatically resumes!

---

## 4. Teardown / Cleanup (Delete Resources to Avoid Billing)
When your viva and demonstration are finished:
1. Go to the **CloudFormation Console**.
2. Select `cn-project` and click **Delete**.
* All 4 EC2 instances, VPC, Security Group, and Internet Gateway will be cleanly deleted in 60 seconds. Total AWS cost: **$0.00** (Free Tier).
