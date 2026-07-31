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
  - name: trivy
    image: aquasec/trivy:latest
    command: ['cat']
    tty: true
  - name: kaniko
    image: gcr.io/kaniko-project/executor:debug
    command: ['cat']
    tty: true
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

        stage('Container Build (Kaniko)') {
            steps {
                container('kaniko') {
                    sh """
                        /kaniko/executor \
                          --context=dir://. \
                          --dockerfile=Dockerfile \
                          --destination=${REGISTRY}/${APP_NAME}:${IMAGE_TAG} \
                          --no-push
                    """
                }
            }
        }

        stage('Trivy Image Scan') {
            steps {
                container('trivy') {
                    sh """
                        trivy image --severity HIGH,CRITICAL \
                          --exit-code 1 \
                          ${REGISTRY}/${APP_NAME}:${IMAGE_TAG}
                    """
                }
            }
        }

        stage('Push Image to ECR') {
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

        stage('Deploy to EKS') {
            steps {
                container('kubectl') {
                    sh """
                        kubectl set image deployment/${APP_NAME} \
                          ${APP_NAME}=${REGISTRY}/${APP_NAME}:${IMAGE_TAG} \
                          -n production
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
                    sh 'python3 scripts/ai_analyst.py console.log > ai_summary.json'
                    sh 'cat ai_summary.json'
                    def aiResult = readFile('ai_summary.json')
                    createSummary(iconPath: 'warning.png', text: "### 🤖 AI Agent Diagnostic\n```json\n${aiResult}\n```")
                }
            }
        }
        always {
            cleanWs()
        }
    }
}