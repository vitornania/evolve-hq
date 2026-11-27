# Evolve HQ

Read the team roster and select the matching catalog action before starting a job. Use the bundled skills and any authorized local overlay as the source for methods. Use Market Research Team for an explicit research sprint and the free local runner for the named local actions.

For a selected skill, read its bundled guide in `skills/<name>/SKILL.md` and the matching authorized method in `.office/libraries/evolve/skills/<name>/SKILL.md` when installed. Resolve each reference from its own file. Use the assigned method and inspect the original material that bears on the decision before attributing a result to it.

Create a task inside this folder for a specific product when the user asks to start work. Preserve the selected product, angle, evidence and asset references across desks. Use the existing role assignments in team/roster.md. Report sequential work as sequential. Review the deliverable before handing it back.

Use `python3 hq.py run ACTION INPUT --product PRODUCT` to run a listed local action and save its task record. For a team sprint, use `python3 hq.py sprint --product PRODUCT --market MARKET --decision DECISION` to make a record. Then follow the Market Research Team skill and save the completed work alongside that record.

Keep the live office current. For sprint steps, run `python3 hq.py update RECORD --role "ROLE" --status working --note "Current step"` immediately before starting each role's actual work. Post an update when the role is blocked, awaiting review, or finished. For a standalone role assignment, start with `python3 hq.py assign --product PRODUCT --title TITLE --role "ROLE" --note "Current step"`, then update the returned record. Local action commands report their own start and result. Show parallel work only while those roles are actually active.

Office Development owns the app and its local integrations. Keep each job with its own inputs and outputs. Request authorization before any live account change, publishing, paid action or outbound contact.
