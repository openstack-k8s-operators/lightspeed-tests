# Lightspeed Tests Playbooks

Ansible playbooks to run the test suite.

The ci-framework Lightspeed stage runs this playbook inside an AnsibleTest Pod.
The test image clones the configured repository, while the job explicitly
projects an authorized client token and collects JUnit and logs from the results
PVC. Both the CI route and standalone example execute a published branch, not
an unmerged Zuul checkout. Required runner fixes must be available in that branch
before the job can use them.

## `run_lightspeed_tests.yaml`

Executes the RHOS Lightspeed test suite using pytest. The playbook:

1. Prepares artifact storage and removes stale results for this report path
2. Records Git source identity when available and checks the source and token file
3. Installs [uv](https://astral.sh/uv) if absent, Python 3.12 and locked dependencies
4. Runs pytest with the configured inputs and token-file authentication
5. Saves pytest/JUnit output and requires executed passing tests
6. Saves runner diagnostics on success or failure

Test results are stored in the location specified by `junit_xml_path`, which the test-operator can consume for reporting.
Pytest output is also saved alongside it as `<junit_xml_path>.log`. The playbook
fails if pytest returns a nonzero exit code, or if the JUnit report is missing,
malformed, empty, entirely skipped, or contains failures or errors. At least
one test must have executed successfully. Reports and pytest output are retained
before this final check, including when tests fail.
An existing results directory retains its ownership and permissions, including
storage mounted by test-operator. Missing results directories are created.

`<junit_xml_path>.runner.log` records the source path, Git revision and tracked
changes when the checkout has Git metadata, runner settings (token path only),
pytest output and the task/message/output of a setup or test failure. A checkout
without `.git` is labelled `unavailable`. The diagnostic log is written on
success and failure once artifact storage is available. Failures remain nonzero.
Old JUnit, pytest output and runner diagnostics are removed before setup, so a
setup failure cannot leave a previous passing report for this report path.
Image startup, repository cloning, fact gathering and inaccessible artifact
storage can fail before these tasks run; inspect the Pod's container logs then.

### Parameters

All parameters can be overridden via the `AnsibleTest` custom resource when running through test-operator.

* `lightspeed_url`: (String) URL of the Lightspeed service to test against. Default value: `https://lightspeed-app-server.openstack-lightspeed.svc.cluster.local:8443`
* `lightspeed_token_file`: (String) File containing the client token. Default value: `/var/run/secrets/kubernetes.io/serviceaccount/token`
* `lightspeed_timeout`: (Integer) Timeout in seconds for Lightspeed API requests. Default value: `30`
* `test_question`: (String) Sample question for testing. Default value: `What is OpenStack?`
* `pytest_args`: (String) Additional arguments to pass to pytest. Default value: `-v --tb=short --color=yes`. The CI Lightspeed stage explicitly selects `tests/integration` for its run.
* `junit_xml_path`: (String) Path where JUnit XML test results will be written. The test-operator provides writable storage at this location. Default value: `/var/lib/AnsibleTests/external_files/test-results.xml`
* `test_suite_path`: (String) Path to the test suite directory. The test-operator clones git repositories to this location. Default value: `{{ ansible_env.HOME }}/ansible`

### Usage

The following example outlines execution through an `AnsibleTest` custom resource.
The test-operator disables automatic service-account token mounting. Before
using the example, create the authorization resources below. The explicit
projected volume supplies a rotating token for the namespace's `default`
ServiceAccount, which the current test-operator uses. `privileged: true` does
not supply this token. The CI stage uses the same mount mechanism and reuses
the existing OpenStack resources instead of the standalone placeholders.

1\. Create a file `lightspeed-auth-resources.yaml` with the following content:

```yaml
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: lightspeed-test-role
rules:
- nonResourceURLs: ["/ls-access"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: lightspeed-test-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: lightspeed-test-role
subjects:
- kind: ServiceAccount
  name: default
  namespace: openstack-lightspeed
```

And run `oc apply -f lightspeed-auth-resources.yaml`. This grants Lightspeed access
to the `default` ServiceAccount in `openstack-lightspeed`. If the supplied token
belongs to a different ServiceAccount, change the binding's subject accordingly.

2\. Create a file `lightspeed-dummy-resources.yaml` with the following content:

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-operator-dummy-config
  namespace: openstack-lightspeed
  labels:
    app: lightspeed-tests
    persistent: "true"
    managed-by: test-operator
data:
  clouds.yaml: |
    # Dummy file - not used by lightspeed tests
    # Required by test-operator but lightspeed tests don't need OpenStack
---
apiVersion: v1
kind: Secret
metadata:
  name: test-operator-dummy-secret
  namespace: openstack-lightspeed
  labels:
    app: lightspeed-tests
    persistent: "true"
    managed-by: test-operator
type: Opaque
stringData:
  secure.yaml: |
    # Dummy file - not used by lightspeed tests
    # Required by test-operator but lightspeed tests don't need OpenStack
---
apiVersion: v1
kind: Secret
metadata:
  name: dataplane-ansible-ssh-private-key-secret
  namespace: openstack-lightspeed
  labels:
    app: lightspeed-tests
    persistent: "true"
    managed-by: test-operator
type: Opaque
stringData:
  ssh-privatekey: |
    # Dummy SSH key - not used by lightspeed tests
```

Run `oc apply -f lightspeed-dummy-resources.yaml`. This will create empty configs that are expected by the test-operator but are not actually used for anything. Without the dummy resources, the test operator will not run the tests.

3\. Create an `AnsibleTest` CR file `lightspeed-ansible-test-cr.yaml` with the following content:

```yaml
---
apiVersion: test.openstack.org/v1beta1
kind: AnsibleTest
metadata:
  name: lightspeed-tests
  namespace: openstack-lightspeed
  labels:
    app.kubernetes.io/name: test-operator
    app.kubernetes.io/managed-by: kustomize
spec:
  openStackConfigMap: test-operator-dummy-config
  openStackConfigSecret: test-operator-dummy-secret
  ansibleGitRepo: https://github.com/openstack-k8s-operators/lightspeed-tests
  # Leave empty to use the cloned repository default branch.
  ansibleGitBranch: ""
  ansiblePlaybookPath: playbooks/run_lightspeed_tests.yaml

  # Ansible inventory - run tests on localhost
  ansibleInventory: |
    localhost ansible_connection=local ansible_python_interpreter=python3

  debug: false
  containerImage: quay.io/podified-antelope-centos9/openstack-ansible-tests:current-podified

  # Storage class for any PVCs (test results, logs)
  # if running in CRC, use crc-csi-hostpath-provisioner
  # if running in OpenShift cluster, use: local-storage
  storageClass: crc-csi-hostpath-provisioner

  # Privileged execution and client authentication are separate settings.
  privileged: true
  # Resource limits for the test pod
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
    requests:
      cpu: 1000m
      memory: 1Gi

  extraMounts:
    - name: lightspeed-client
      extraVol:
        - propagation: [AnsibleTest]
          extraVolType: Undefined
          volumes:
            - name: lightspeed-client-token
              projected:
                sources:
                  - serviceAccountToken:
                      path: token
                      expirationSeconds: 3600
          mounts:
            - name: lightspeed-client-token
              mountPath: /lightspeed-auth
              readOnly: true

  # Variables passed to Ansible playbook
  ansibleVarFiles: |
    ---
    # Lightspeed service URL (defaults to in-cluster service)
    lightspeed_url: "https://lightspeed-app-server.openstack-lightspeed.svc.cluster.local:8443"
    lightspeed_timeout: 30
    lightspeed_token_file: /lightspeed-auth/token
    # Same value as the Goose container's LIGHTSPEED_MODEL
    lightspeed_model: "<your configured model>"
    test_question: "What is OpenStack?"
    # Pytest options
    pytest_args: "-v --tb=short --color=yes"
    # JUnit XML output path (test-operator writable location)
    junit_xml_path: "/var/lib/AnsibleTests/external_files/test-results.xml"
```
After creating the authorization and prerequisite resources, run
`oc apply -f lightspeed-ansible-test-cr.yaml` to run the test suite.
