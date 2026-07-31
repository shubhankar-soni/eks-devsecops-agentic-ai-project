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
        APP_NAME       = 'demo-microservice'
        REGISTRY       = '123456789012.dkr.ecr.us-east-1.amazonaws.com'
        OPENAI_API_KEY = credentials('openai-api-key') // Stored in Jenkins Credentials Manager
    }

    stages {
        stage('Unit Test') {
            steps {
                container('gradle') {
                    sh './gradlew test'
                }
            }
        }
        
        stage('Trivy Security Scan') {
            steps {
                container('trivy') {
                    sh 'trivy fs --severity HIGH,CRITICAL --exit-code 1 .'
                }
            }
        }

        // Additional stages (Sonar, Kaniko, Deploy)...
    }

    post {
        failure {
            container('python-agent') {
                script {
                    echo "⚠️ Build Failed! Triggering AI Agent to diagnose root cause..."
                    
                    // 1. Fetch raw build logs using Jenkins API or console output
                    sh 'curl -s "${BUILD_URL}consoleText" > console.log'
                    
                    // 2. Run the AI agent analysis script
                    sh 'python3 scripts/ai_analyst.py console.log > ai_summary.json'
                    
                    // 3. Print the AI diagnosis directly into the console log
                    sh 'cat ai_summary.json'
                    
                    // 4. Publish AI diagnosis to the Jenkins Build Page HTML summary
                    def aiResult = readFile('ai_summary.json')
                    createSummary(iconPath: 'warning.png', text: "### 🤖 AI Agent Diagnostic\n```json\n${aiResult}\n```")
                }
            }
        }
    }
}