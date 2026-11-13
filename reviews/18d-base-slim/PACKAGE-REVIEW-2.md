No outstanding findings in `e5e89d2d..HEAD`. All three requested fixes are present; I found no regressions caused by them.

- **Push checks fixed:** [base workflow](.github/workflows/control-base.yml:6) and [boundary workflow](.github/workflows/control-boundary.yml:3) restore branch push checks. Boundary also restores `main` pushes and prevents cancellation on `main`.
- **Boundary filters fixed:** both event filters use `control/**`, covering definitions and generated inputs.
- **Testapp asks fixed:** [default policy](control/aresos_control/boundary_policy.py:20) includes both rules, generated settings match, and the boundary requires them. Generator guards reject misnamed rules and missing non-testapp servers. Regression tests cover both missing-rule refusals and adapter coverage; documentation explains testapp and Chrome integration.

Generated-artifact checks, workflow assertions, targeted policy/admission probes, and ten evidence-validator tests passed. Admission probes mocked the settings reader; full Linux integration suites were not rerun in this read-only workspace.

SAFE