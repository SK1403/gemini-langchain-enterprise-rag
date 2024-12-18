# SRE & DevOps Disaster Recovery Runbook: Cloud Outage & Failover
Document ID: RUNBOOK-SRE-2024-FAILOVER
Owner: Principal Site Reliability Engineering Team
Last Reviewed: August 2024

## 1. Incident Classification and Escalation
- **Sev-1 (Critical Outage)**: Primary region (us-central1) unreachable, customer API error rate > 5%.
- Escalation: Page on-call primary SRE via PagerDuty (Schedule: `sre-tier1-core`).
- War Room: Join Google Meet `meet.google.com/sec-prod-emergency` within 10 minutes of page.

## 2. Automated Regional Failover Protocol
When us-central1 experiences extended disruption (> 15 minutes), initiate regional failover to europe-west1:

1. **Traffic Rerouting via Cloud DNS / Global Anycast**:
   ```bash
   gcloud compute backend-services update enterprise-rag-lb \
       --global \
       --set-backends=europe-west1-neg
   ```

2. **Activate Secondary Database Replica**:
   ```bash
   gcloud alloydb instances promote-secondary corp-db-dr-replica \
       --cluster=corp-dr-cluster \
       --region=europe-west1
   ```

3. **Verify Health Endpoints**:
   - Query `https://api.corp.internal/_stcore/health`
   - Ensure latency is < 200ms and HTTP 200 is returned across all pods.

## 3. Recovery Time Objective (RTO) & Recovery Point Objective (RPO)
- **Target RTO**: Less than 30 minutes from initial declaration.
- **Target RPO**: Less than 5 minutes data loss via asynchronous replication.
