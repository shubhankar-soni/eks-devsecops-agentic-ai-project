pipeline {
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
metadata:
  labels:
    component: jenkins-agent
spec:
  containers:
  - name: gradle
    image: gradle:8.5-jdk17
    command: ['cat']
    tty: true
    resources:
      requests:
        cpu: "500m"
        memory: "512Mi"
      limits:
        cpu: "2"
        memory: "2Gi"
  - name: trivy
    image: aquasec/trivy:latest
    command: ['cat']
    tty: true
    resources:
      requests:
        cpu: "200m"
        memory: "256Mi"
      limits:
        cpu: "1"
        memory: "1Gi"
  - name: kaniko
    image: gcr.io/kaniko-project/executor:debug
    command: ['cat']
    tty: true
    resources:
      requests:
        cpu: "500m"
        memory: "512Mi"
      limits:
        cpu: "2"
        memory: "2Gi"
  - name: kubectl
    image: bitnami/kubectl:latest
    command: ['cat']
    tty: true
  - name: python-agent
    image: python:3.11-slim
    command: ['cat']
    tty: true
'''
        }
    }

    environment {
        APP_NAME        = 'devsecops-app'
        REGISTRY        = "${env.ECR_REGISTRY}"
        IMAGE_TAG       = "${env.BUILD_NUMBER}"
        SONAR_SERVER    = 'sonar-server'
        AWS_REGION      = 'us-east-1'
        OPENAI_API_KEY  = credentials('openai-api-key')
    }

    stages {
        stage('Source Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Unit Test & Coverage') {
            steps {
                container('gradle') {
                    sh '''
                        gradle wrapper --gradle-version 8.5
                        chmod +x ./gradlew
                        ./gradlew test jacocoTestReport
                    '''
                }
            }
            post {
                always {
                    script {
                        try {
                            junit 'build/test-results/test/*.xml'
                        } catch(Exception e) {
                            echo "No JUnit report found to publish."
                        }
                    }
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                container('gradle') {
                    withSonarQubeEnv(SONAR_SERVER) {
                        sh '''
                            ./gradlew sonar \
                              -Dsonar.projectKey=${APP_NAME} \
                              -Dsonar.coverage.jacoco.xmlReportPaths=build/reports/jacoco/test/jacocoTestReport.xml
                        '''
                    }
                }
            }
        }

        stage('SonarQube Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

stage('Container Build & Push (Kaniko)') {
            steps {
                container('kaniko') {
                    sh """
                        /kaniko/executor \
                          --context=dir://. \
                          --dockerfile=Dockerfile \
                          --destination=${REGISTRY}/${APP_NAME}:${IMAGE_TAG}
                    """
                }
            }
        }

        stage('Trivy Security Scan') {
            steps {
                container('trivy') {
                    // Scanning filesystem (. ) avoids needing remote registry auth or docker daemon socket
                    sh """
                        trivy fs --severity HIGH,CRITICAL \
                          --exit-code 1 \
                          .
                    """
                }
            }
        }


        stage('Deploy to EKS') {
                steps {
                    container('kubectl') {
                        sh """
                            # Substitute the dynamic image tag into the deployment manifest
                            sed -i 's|IMAGE_PLACEHOLDER|${REGISTRY}/demo-microservice/${APP_NAME}:${IMAGE_TAG}|g' k8s/deployment.yaml
                            
                            # Apply all manifests in the k8s directory
                            kubectl apply -f k8s/*.yaml -n production
                            
                            # Verify deployment rollouts successfully
                            kubectl rollout status deployment/${APP_NAME} -n production --timeout=120s
                        """
                    }
                }
            }
        }

    post {
        failure {
            container('python-agent') {
                script {
                    echo "⚠️ Build Failed! Triggering AI Agent to diagnose root cause..."
                    sh 'apt-get update && apt-get install -y curl'
                    sh 'curl -s "${BUILD_URL}consoleText" > console.log'
                    // Handles error gracefully if OpenAI rate limits (429) occur
                    sh 'python3 scripts/ai_analyst.py console.log > ai_summary.json || true'
                    sh 'cat ai_summary.json || echo "AI Summary skipped due to API limits."'
                }
            }
        }
        always {
            deleteDir()
        }
    }
}