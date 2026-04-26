pipeline {
  agent none

  parameters {
    string(
      name: 'GIT_BRANCH',
      defaultValue: 'main',
      description: 'Git branch to build/deploy'
    )
  }

  environment {
    REPO_URL    = "https://github.com/gbalaji-hbox/medical_db.git"
    COMPOSE_DIR = "/home/balaji.g/docker-compose/medical-db"
  }

  stages {

    stage("Build (jenkins-agent)") {
      agent { label "jenkins-agent" }

      stages {

        stage("Checkout") {
          steps {
            dir("medical-db") {
              git branch: "${params.GIT_BRANCH}",
                  url: "${env.REPO_URL}",
                  credentialsId: "github-credentials"
            }
          }
        }

        stage("Inject Env File") {
          steps {
            withCredentials([file(credentialsId: 'medical_db_env', variable: 'ENV_FILE')]) {
              sh '''
                set -e
                cp "$ENV_FILE" medical-db/.env
                chmod 600 medical-db/.env
                echo "Backend env injected successfully"
              '''
            }
          }
        }

        stage("Stash Artifacts") {
          steps {
            stash name: "app-artifacts",
                  includes: "medical-db/**"
          }
        }
      }
    }

    stage("Deploy (docker-agent)") {
      agent { label "docker-agent" }

      steps {
        unstash "app-artifacts"

        sh """
          set -e

          echo "=== SYNC CODE TO SERVER ==="
          mkdir -p ${COMPOSE_DIR}
          rsync -a --delete \\
            --exclude='.git' \\
            --exclude='backups' \\
            --exclude='data' \\
            medical-db/ ${COMPOSE_DIR}/

          echo "=== ENSURE PERMISSIONS ==="
          mkdir -p ${COMPOSE_DIR}/data ${COMPOSE_DIR}/backups
          chmod 777 ${COMPOSE_DIR}/data
          chmod 644 ${COMPOSE_DIR}/.env

          echo "=== VERIFY REQUIRED FILES ==="
          test -f ${COMPOSE_DIR}/.env              || { echo "ERROR: .env missing";              exit 1; }
          test -f ${COMPOSE_DIR}/Dockerfile        || { echo "ERROR: Dockerfile missing";        exit 1; }
          test -f ${COMPOSE_DIR}/docker-compose.yml || { echo "ERROR: docker-compose.yml missing"; exit 1; }

          echo "=== BUILD IMAGES ==="
          cd ${COMPOSE_DIR}
          COMPOSE_BAKE=false docker compose build --no-cache

          echo "=== DEPLOY SERVICES ==="
          for SERVICE in api frontend db-backup; do
            CONTAINER=\$(docker compose ps -q \${SERVICE} 2>/dev/null || true)
            if [ -n "\${CONTAINER}" ]; then
              echo "Recreating existing container: \${SERVICE}"
              docker compose up -d --no-deps --force-recreate \${SERVICE}
            else
              echo "Creating new container: \${SERVICE}"
              docker compose up -d --no-deps \${SERVICE}
            fi
          done

          echo "=== SERVICE STATUS ==="
          docker compose ps
        """
      }
    }
  }

  post {
    success {
      node('docker-agent') {
        sh """
          cd ${COMPOSE_DIR}
          echo "=== Deployment successful — running containers ==="
          docker compose ps
        """
      }
    }
    failure {
      node('docker-agent') {
        sh """
          cd ${COMPOSE_DIR} || true
          echo "=== Container status ==="
          docker compose ps || true
          echo "=== API logs ==="
          docker compose logs --tail=200 api || true
          echo "=== Frontend logs ==="
          docker compose logs --tail=200 frontend || true
          echo "=== Backup sidecar logs ==="
          docker compose logs --tail=50 db-backup || true
        """
      }
    }
  }
}
