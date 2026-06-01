# Review Rules

Rules for agents assisting with human review flows.

- Agents assist with review preparation; approval or rejection stays a human decision.
- Check specification compliance: does the casting match every specified behavior?
- Check interface contract compliance: are contracts honored? Any silent changes?
- Check test coverage: does every specification behavior have a passing test forming a credible quality gate?
- Check scope creep: is there code implementing behavior absent from the specification?
- Check commit hygiene: are commits atomic and traceable to specification sections?
- Check introduced dependencies: are imports and libraries allowed by architecture documents?
- Produce a review summary listing: checks that passed, potential issues, and items requiring explicit human judgment.
- Flag findings; do not silently fix substantive issues discovered during assistance. Human reviewers decide remedial action unless the assigned agent task separately authorizes fixes.
- When implementation diverges from the specification, quote the specification section alongside the diverging implementation or commit reference.
