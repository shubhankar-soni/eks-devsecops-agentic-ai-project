# AWS EKS DevSecOps Agentic AI Project

<p align="center">
  <!-- Python -->
  <a href="https://www.python.org" target="_blank">
    <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  </a>
  &nbsp;
  <!-- Gemini LLM -->
  <a href="https://deepmind.google/technologies/gemini/" target="_blank">
    <img src="https://img.shields.io/badge/Google%20Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white" alt="Google Gemini" />
  </a>
  &nbsp;
  <!-- Java -->
  <a href="https://www.java.com" target="_blank">
    <img src="https://img.shields.io/badge/Java-ED8B00?style=flat-square&logo=openjdk&logoColor=white" alt="Java" />
  </a>
  &nbsp;
  <!-- Gradle -->
  <a href="https://gradle.org" target="_blank">
    <img src="https://img.shields.io/badge/Gradle-02303A?style=flat-square&logo=gradle&logoColor=white" alt="Gradle" />
  </a>
  &nbsp;
  <!-- JUnit -->
  <a href="https://junit.org/junit5/" target="_blank">
    <img src="https://img.shields.io/badge/JUnit5-25A162?style=flat-square&logo=junit5&logoColor=white" alt="JUnit" />
  </a>
  &nbsp;
  <!-- JaCoCo -->
  <a href="https://www.eclemma.org/jacoco/" target="_blank">
    <img src="https://img.shields.io/badge/JaCoCo-C71A36?style=flat-square&logo=eclipseide&logoColor=white" alt="JaCoCo" />
  </a>
  &nbsp;
  <!-- SonarQube -->
  <a href="https://www.sonarqube.org/" target="_blank">
    <img src="https://img.shields.io/badge/SonarQube-4E9BCD?style=flat-square&logo=sonarqube&logoColor=white" alt="SonarQube" />
  </a>
  &nbsp;
  <!-- Kubernetes -->
  <a href="https://kubernetes.io" target="_blank">
    <img src="https://img.shields.io/badge/Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white" alt="Kubernetes" />
  </a>
  &nbsp;
  <!-- AWS -->
  <a href="https://aws.amazon.com" target="_blank">
    <img src="https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazon-aws&logoColor=FF9900" alt="AWS" />
  </a>
</p>

## Pre-requisites
- aws cli, eksctl, kubectl, helm packages should be installed.

## 1) Login to AWS
- `aws login` — login to the iam profile.
- Avoid logging in using root user in aws; instead create an IAM user with required roles and policies attached.

## 2) Create EKS cluster
1. Create `cluster.yaml` for the EKS cluster.
2. Create the cluster:
   ```bash
   eksctl create cluster -f eks/cluster.yaml
   ```
3. Once created, check the nodes:
   ```bash
   kubectl get nodes
   ```

## 3) Enable Storage & Install AWS EBS CSI Driver
```bash
##
eksctl utils associate-iam-oidc-provider \
  --cluster devops-project-cluster \
  --region us-east-1 \
  --approve

##
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster devops-project-cluster \
  --region us-east-1 \
  --role-name AmazonEKS_EBS_CSI_DriverRole \
  --role-only \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve

##
eksctl create addon \
  --name aws-ebs-csi-driver \
  --cluster devops-project-cluster \
  --region us-east-1 \
  --service-account-role-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/AmazonEKS_EBS_CSI_DriverRole \
  --force

##
kubectl patch storageclass gp2 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

## 4) Deploy SonarQube on EKS
```bash
helm repo add sonarqube https://SonarSource.github.io/helm-chart-sonarqube
helm repo update
kubectl create ns sonarqube
helm install sonarqube sonarqube/sonarqube --namespace sonarqube \
  --set service.type=LoadBalancer \
  --set monitoringPasscode="YourStrongPassword" \
  --set community.enabled=true
```

### Sample output (reference)
```
NAME: sonarqube
LAST DEPLOYED: Fri Jul 31 18:09:04 2026
NAMESPACE: sonarqube
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
NOTES:
1. Get the application URL by running these commands:
   NOTE: It may take a few minutes for the LoadBalancer IP to be available.
   You can watch the status of by running 'kubectl get svc -w sonarqube-sonarqube'
   export SERVICE_IP=$(kubectl get svc --namespace sonarqube sonarqube-sonarqube -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
   echo http://$SERVICE_IP:9000
WARNING: Please note that the SonarQube image runs with a non-root user (uid=1000) belonging to the root group (guid=0).
WARNING: Setting the deployment strategy type is deprecated and will be removed in a future release.
WARNING: The deploymentType value is deprecated and won't be supported anymore.
```

### Access SonarQube
- Get the EXTERNAL-IP / domain:
  ```bash
  kubectl get svc -w sonarqube-sonarqube -n sonarqube
  ```
- Open: `http://:9000`
  - Example: http://342349009.us-east-1.elb.amazonaws.com:9000
- Default creds: `admin/admin`

### SonarQube: Generate token
- Go to **Administration > Security > Users > Tokens**
- Generate a token named `jenkins-sonar-token` and copy it.

### SonarQube: Configure webhook
- Go to **Administration > Configuration > Webhooks**
- Create webhook named `jenkins-webhook` pointing to:
  - `http://<JENKINS-URL>:8080/sonarqube-webhook/`
- Replace `<JENKINS-URL>` with the real Jenkins URL later.

## 5) Deploy Jenkins Controller on EKS
### 5.1 Add Jenkins Helm repo
```bash
helm repo add jenkins https://charts.jenkins.io
helm repo update
```

### 5.2 Create Jenkins namespace + service account + RBAC
```bash
kubectl create namespace jenkins
kubectl create serviceaccount jenkins-admin -n jenkins
kubectl create clusterrolebinding jenkins-admin-binding \
  --clusterrole=cluster-admin \
  --serviceaccount=jenkins:jenkins-admin
```

### 5.3 Install Jenkins via Helm
```bash
helm install jenkins jenkins/jenkins \
  --namespace jenkins \
  --set controller.serviceType=LoadBalancer \
  --set controller.serviceAccount.name=jenkins-admin
```

### 5.4 Get Jenkins admin password
```bash
kubectl get secret -n jenkins jenkins -o jsonpath="{.data.jenkins-admin-password}" | base64 --decode; echo
```

### 5.5 Access Jenkins
- Use the `EXTERNAL-IP` of:
  ```bash
  kubectl get svc -n jenkins
  ```
- Replace the domain name in the SonarQube Jenkins webhook with the original Jenkins domain generated in the previous step.
- Login: `admin/`

## 6) Configure Jenkins Plugins & Credentials
### Install plugins
Go to **Manage Jenkins > Plugins > Available Plugins** and install:
- `Kubernetes`
- `SonarQube Scanner`
- `Pipeline: Stage View`
- `Pipeline Utility Steps`
- `Email Extension Plugin`

### Add SonarQube credentials
Go to **Manage Jenkins > Credentials > System > Global credentials > Add Credentials**:
- Kind: `Secret text`
- Secret: SonarQube token from Phase 3
- ID: `sonarqube-token`

### Connect SonarQube system
Go to **Manage Jenkins > System** → **SonarQube servers** → **Add SonarQube**:
- Name: `sonar-server` (must match `Jenkinsfile`)
- Server URL: `http://sonarqube-sonarqube.sonarqube.svc.cluster.local:9000` (internal EKS DNS)
- Server authentication token: `sonarqube-token`

## 7) Create ECR registry
```bash
aws ecr create-repository --repository-name demo-microservice/devsecops-app --region us-east-1
```

### Attach ECR permissions to node role
1. Open **AWS IAM Console**.
2. Click **Roles**.
3. Select node instance role: `eksctl-devops-project-cluster-node-NodeInstanceRole-...`
4. Permissions → **Add permissions** → **Attach policies**
5. Attach `AmazonEC2ContainerRegistryPowerUser` (or `AmazonEC2ContainerRegistryFullAccess`).

## 8) Create Production Namespace
Create the namespace where the application will be deployed.

```bash
kubectl create namespace production
kubectl get namespace production
```

Do this **before** applying deployment resources. This avoids the issue where the Namespace and Deployment were submitted together and the API server attempted to create the Deployment before the namespace was available.

## 9) Create Jenkins Agent ServiceAccount and RBAC
Your dynamically created Jenkins agent pods run inside the `jenkins` namespace but need permission to deploy resources into the `production` namespace.

```bash
kubectl apply -f eks/jenkins-agent-rbac.yaml
```

## 10) Create Gemini API key
Create a Gemini API key for the AI failure-analysis component.

Store it in Jenkins:
- Manage Jenkins
- → Credentials
- → System
- → Global credentials
- → Add Credentials

Configure:
- Kind: `Secret text`
- Secret: ``
- ID: `gemini-api-key`

The Jenkinsfile can expose it to the Python agent with:
```groovy
template { 
  GEMINI_API_KEY = credentials('gemini-api-key')
}
```

## 11) Create Jenkins API token
The failure-analysis process needs permission to retrieve the Jenkins build's console log.

- Log in to Jenkins with a user that can read the pipeline.
- Navigate to: User Profile → Security → API Token → Add new Token → Generate  (ID: jenkins-api-token)
- Copy the generated API token.

## 12) Store Jenkins API credentials
Go to:
- Manage Jenkins
- → Credentials
- → System
- → Global credentials
- → Add Credentials

Configure:
- Kind: **Username with password**
- Username: `<YOUR ACTUAL JENKINS USERNAME>`
- Password: `<YOUR GENERATED API TOKEN>`
- ID: `jenkins-api-token`

## 13) Configure Gmail for Jenkins notifications
The Google account used for Jenkins notifications needs **2-Step Verification** enabled.

Create a Google **App Password** for Jenkins.

Do not use the normal Google account password.

## 14) Add Gmail credentials to Jenkins
Go to:
- Manage Jenkins
- → Credentials
- → System
- → Global credentials
- → Add Credentials

Configure:
- Kind: **Username with password**
- Username: `your-email@gmail.com`
- Password: `<the 16-character Google App Password>`
- ID: `gmail-smtp`

---

## 15) Configure Jenkins SMTP
Go to: **Manage Jenkins → System →Extended E-mail Notification**

Configure:
- SMTP Server: `smtp.gmail.com`
- SMTP Port: `587`
- Credentials: `gmail-smtp`
- Use SSL: `No`
- Use TLS: `Yes`
- Use OAuth 2.0: `No`

Also configure **E-mail Notification** if required by the Jenkins installation.
Use the same Gmail SMTP settings.

---

## 16) Configure Jenkins sender address
Go to: **Manage Jenkins → System → Jenkins Location**

Set:
- System Admin e-mail address: ``

Save the configuration.

---

## 17) Test email notification
Under: **Manage Jenkins → System → E-mail Notification**

Use: **Test configuration by sending test e-mail**

Enter the recipient address and confirm that the test email arrives successfully.
Do this before integrating email with the pipeline.

---

## 18) Configure Jenkins pipeline environment
Your Jenkinsfile needs environment variables similar to:
```groovy
environment {
    APP_NAME       = 'devsecops-app'
    REGISTRY       = "${env.ECR_REGISTRY}"
    IMAGE_TAG      = "${env.BUILD_NUMBER}"
    SONAR_SERVER   = 'sonar-server'
    AWS_REGION     = 'us-east-1'
    GEMINI_API_KEY = credentials('gemini-api-key')
}
```

Make sure `ECR_REGISTRY` is defined appropriately for your Jenkins environment/job.

## 19) Destroy the EKS cluster and ECR Registry
   ```bash
   eksctl delete cluster --name devops-project-cluster --region us-east-1
   ```
  To delete ECR Registry: **AWS Console → Aamazon ECR → Private Registry → Repositories → Delete the Private Registry create in initial step**