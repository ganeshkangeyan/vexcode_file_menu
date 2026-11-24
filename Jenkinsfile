// VEXcode File Menu regression suite.
//
// Scheduled: weekday nights, all five production sites, Chromium, every test.
// Manual ("Build with Parameters"): pick sites / a test-build URL / browser /
// a marker subset. All the logic lives in tools/run_ci.py -- this file only
// sets up Python and calls it.
//
// AGENT REQUIREMENTS -- read before the first run:
//   * Python 3.10+ on PATH (`python3` on Linux, `python` on Windows).
//   * The browsers must run HEADED: Cloudflare in front of the VEXcode sites
//     blocks headless Chrome (every test errors on "Performing security
//     verification"). So:
//       - Linux agent: install xvfb (`apt-get install xvfb`); this file wraps
//         the run in `xvfb-run` automatically. Also run once, as root:
//         `python3 -m playwright install-deps chromium`.
//       - Windows agent: the agent must run in a logged-in desktop session
//         (agent started from a user login / auto-logon), not as a Windows
//         service in session 0.
//     Or ask VEX to allow-list the agent's IP in Cloudflare and run headless
//     (env VEX_HEADLESS=1). Never try to disguise headless as a real browser.
//   * BROWSER=msedge uses the Microsoft Edge installed on the agent.
//   * Give the job the "vexcode-ui" label on that agent (or change the label).

pipeline {
    agent { label 'vexcode-ui' }

    triggers {
        // Weekday nights around 1 AM (H spreads the exact minute). Scheduled
        // builds use the parameter defaults below.
        cron('H 1 * * 1-5')
    }

    parameters {
        string(name: 'SITES', defaultValue: 'all',
               description: "'all', or a comma list of: v5, 123, go, exp, iq")
        string(name: 'TEST_URL', defaultValue: '',
               description: 'Optional test-build URL to run INSTEAD of production. Set SITES to exactly that product (e.g. v5). Its examples are compared with the production baseline.')
        choice(name: 'BROWSER', choices: ['chromium', 'msedge'],
               description: 'Firefox is not offered: VEXcode itself refuses to run in Firefox.')
        string(name: 'MARKERS', defaultValue: '',
               description: "Optional pytest -m expression to run a subset, e.g. 'save or save_as'. Markers: new_project, unsaved_changes, open, open_recent, open_examples, save, save_as, whats_new, about. Empty = everything.")
    }

    options {
        timeout(time: 5, unit: 'HOURS')   // a full 5-site run takes ~1.5 h
        disableConcurrentBuilds()          // two runs on one agent overload it
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    environment {
        VEX_SLOWMO = '1'
        PYTHONUNBUFFERED = '1'
        PYTHONIOENCODING = 'utf-8'
    }

    stages {
        stage('Setup') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            python3 -m venv .venv
                            .venv/bin/python -m pip install -q --upgrade pip
                            .venv/bin/python -m pip install -q -r requirements.txt
                            .venv/bin/python -m playwright install chromium
                        '''
                    } else {
                        bat '''
                            python -m venv .venv
                            .venv\\Scripts\\python -m pip install -q --upgrade pip
                            .venv\\Scripts\\python -m pip install -q -r requirements.txt
                            .venv\\Scripts\\python -m playwright install chromium
                        '''
                    }
                }
            }
        }

        stage('Test') {
            steps {
                script {
                    // Parameters reach tools/run_ci.py as env vars (SITES,
                    // TEST_URL, BROWSER, MARKERS) -- no shell quoting needed.
                    int rc = isUnix()
                        ? sh(returnStatus: true, script: 'xvfb-run -a --server-args="-screen 0 1920x1080x24" .venv/bin/python tools/run_ci.py')
                        : bat(returnStatus: true, script: '.venv\\Scripts\\python tools\\run_ci.py')
                    if (rc == 1) {
                        unstable('Some tests failed -- see Test Results and the HTML reports in Build Artifacts.')
                    } else if (rc != 0) {
                        error("Test run could not complete (exit ${rc}) -- see the console log.")
                    }
                }
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/*.xml'
            archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/*.html, reports/*.log'
        }
    }
}
