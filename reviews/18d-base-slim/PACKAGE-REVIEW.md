Reviewed `f3d2f895` against `d3babf1f` and section 7 from `origin/main`.

1. **should-fix — Required push checks were removed.**  
   Where: [control-base.yml:4](.github/workflows/control-base.yml:4), [control-boundary.yml:2](.github/workflows/control-boundary.yml:2).  
   Both workflows now run only for pull requests or manual dispatch, contrary to the brief’s explicit push requirement. This matters immediately: the report says merge conflicts prevent PR checks, so subsequent branch pushes receive no automatic validation.  
   **Fix:** restore path-filtered push triggers for `pkg/18d-base-slim`.

2. **should-fix — Native verification misses changes to its new inputs.**  
   Where: [control-boundary.yml:4](.github/workflows/control-boundary.yml:4).  
   The filter excludes `control/aresos_control/**` and `control/generated/**`. Editing shared instructions and regenerating descriptions can therefore leave the boundary workflow untriggered. Base tests can pass without rerunning the native check that proves the complete instructions reach the model—the central safeguard for removing repeated descriptions.  
   **Fix:** include those directories, or use `control/**`, in both event filters.

I found no blocking tool-safety defect in the reviewed implementation. Independent inspection of the retained final-head receiver log confirmed all 24 precedence cases, including fourteen blocked sends and four `PermissionRequest` approvals matching the accepted residual. Shared-text extraction preserved all 51 actions’ specific guidance and schemas.

Generated-artifact checks and ten evidence-validator tests passed locally. I inspected retained container evidence; I did not rerun the containers.

CHANGES-NEEDED