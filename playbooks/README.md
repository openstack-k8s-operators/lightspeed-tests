# Lightspeed Tests Playbooks

Ansible playbooks to run the test suite.

The ci-framework controller hook can run this playbook against a deployed instance.
The hook supplies an existing test checkout, a Lightspeed API URL, and a
short-lived client token file. It also provides the writable JUnit output path.
Execution through test-operator requires an explicitly supplied client token
file in the test Pod, as described below.

## `run_lightspeed_tests.yaml`

Executes the RHOS Lightspeed test suite using pytest. The playbook:

1. Installs the [uv](https://astral.sh/uv) package manager if not already available
2. Installs Python 3.12 using uv
3. Verifies the supplied test checkout exists
4. Reads the supplied token file for authentication
5. Installs the dependencies recorded in `uv.lock` using uv
6. Runs the pytest test suite with configurable arguments
7. Generates JUnit XML test results for reporting

Test results are stored in the location specified by `junit_xml_path`, which the test-operator can consume for reporting.
Pytest output is also saved alongside it as `<junit_xml_path>.log`. The playbook
fails if pytest returns a nonzero exit code or the JUnit report is missing.
An existing results directory retains its ownership and permissions, including
storage mounted by test-operator. Missing results directories are created.

### Parameters

All parameters can be overridden via the `AnsibleTest` custom resource when running through test-operator.

* `lightspeed_url`: (String) URL of the Lightspeed service to test against. Default value: `https://lightspeed-app-server.openstack-lightspeed.svc.cluster.local:8443`
* `lightspeed_token_file`: (String) File containing the client token. Default value: `/var/run/secrets/kubernetes.io/serviceaccount/token`
* `lightspeed_timeout`: (Integer) Timeout in seconds for Lightspeed API requests. Default value: `30`
* `test_question`: (String) Sample question for testing. Default value: `What is OpenStack?`
* `pytest_args`: (String) Additional arguments to pass to pytest. Default value: `-v --tb=short --color=yes`. The CI controller hook explicitly selects `tests/integration` for its run.
* `junit_xml_path`: (String) Path where JUnit XML test results will be written. The test-operator provides writable storage at this location. Default value: `/var/lib/AnsibleTests/external_files/test-results.xml`
* `test_suite_path`: (String) Path to the test suite directory. The test-operator clones git repositories to this location. Default value: `{{ ansible_env.HOME }}/ansible`

### Usage

The following example outlines execution through an `AnsibleTest` custom resource.
The test-operator disables automatic service-account token mounting. Before
using the example, provide an authorized client token through an explicit mount
supported by your installed test-operator and set `lightspeed_token_file` to its
path in the Pod. The example below does not include that mount configuration;
`privileged: true` does not supply it. The controller hook supplies a temporary
token file separately and does not use this example CR.

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
  ansibleGitBranch: main
  ansiblePlaybookPath: playbooks/run_lightspeed_tests.yaml

  # Ansible inventory - run tests on localhost
  ansibleInventory: |
    localhost ansible_connection=local ansible_python_interpreter=python3

  debug: true
  containerImage: quay.io/podified-antelope-centos9/openstack-ansible-tests:current-podified

  # Storage class for any PVCs (test results, logs)
  # if running in CRC, use crc-csi-hostpath-provisioner
  # if running in OpenShift cluster, use: local-storage
  storageClass: crc-csi-hostpath-provisioner

  # Privileged execution does not mount a client token; configure that separately.
  privileged: true
  # Resource limits for the test pod
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
    requests:
      cpu: 1000m
      memory: 1Gi

  # Variables passed to Ansible playbook
  ansibleVarFiles: |
    ---
    # Lightspeed service URL (defaults to in-cluster service)
    lightspeed_url: "https://lightspeed-app-server.openstack-lightspeed.svc.cluster.local:8443"
    lightspeed_timeout: 30
    # Same value as the Goose container's LIGHTSPEED_MODEL
    lightspeed_model: "<your configured model>"
    test_question: "What is OpenStack?"
    # Pytest options
    pytest_args: "-v --tb=short --color=yes"
    # JUnit XML output path (test-operator writable location)
    junit_xml_path: "/var/lib/AnsibleTests/external_files/test-results.xml"
```
After configuring the token mount and `lightspeed_token_file`, run
`oc apply -f lightspeed-ansible-test-cr.yaml` to run the test suite.
