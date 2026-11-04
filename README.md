# OhUrTeach Workspace

OhUrTeach Workspace is a native Expert Team for Indonesian teachers. It turns one licensed source into a lesson plan, quiz and slide outline. Every draft is reviewed against a versioned rule pack, and final content waits for human approval before publication.

Package ID: `ohurteach-workspace` | Version: 1.1.1 | Status: candidate package with bundled rule pack `RP-OHURTEACH v1.0.1`, invocation not yet verified end to end.

## Type

Team (multi-role collaboration). The Head coordinates; members return results to the Head.

## Members

| Agent ID | Role |
|---|---|
| ohurteach-workspace-team-lead | Head: coordinator |
| ohurteach-workspace-researcher | Sources, provenance, sufficiency, conflicts |
| ohurteach-workspace-planner | Learning blueprint |
| ohurteach-workspace-writer | Content and revisions |
| ohurteach-workspace-reviewer | Rule pack review of every draft |

## Usage examples

- Turn the source material I provide into a lesson plan, quiz and slide outline.
- Make a quiz only from my licensed material, with the teacher key kept separate.
- Fill my school template using a copy, and check layout before and after.

## Current status

- **Structure check:** the package passes the expert-manager validator (0 errors, 0 warnings) when placed in the expert directory.
- **Registration:** registered locally in the `my-experts` marketplace and in the user's expert list. Whether the card shows in My Experts has not been confirmed.
- **Member invocation: not verified.** One attempt to start the Researcher as a native member from a general session failed with "Task agent ohurteach-workspace-researcher is not available". The member never ran, so there was no handoff, no draft and no review. The cause is not proven. In that session the OhUrTeach members did not appear among the observable agent types, and the team had not been summoned from My Experts. A test from a session started by summoning OhUrTeach Workspace is still pending.

## Not yet tested

- Head starting collaboration as the primary agent of a summoned session.
- Calls to the Researcher, Planner, Writer and Reviewer, and the replies they return to the Head.
- The reject, remediate and PASS cycle, the three-review limit and escalation.
- Handling of forbidden claims (cure claims, non-drug products called drugs, halal claims without valid certification).
- Permission checks on sources, and tool access available to members.
- School template filling.
- Optional extras: tone matching, covers, trilingual versions, rule proposals.

## Known limits

- Review counters, permission checks and run records are enforced by instructions in the prompts, not by runtime controls.
- The bundled rule pack `RP-OHURTEACH v1.0.1` (in `skills/ohurteach-rulepack/SKILL.md`) is a prompt-level builder draft, not an official legal or publisher rule pack. Sources and school templates remain unbundled.

## Missing assets

- Avatars are not included. `plugin.json` declares these files, which do not exist yet:
  `avatars/team.png`, `avatars/ohurteach-workspace-team-lead.png`, `avatars/ohurteach-workspace-researcher.png`, `avatars/ohurteach-workspace-planner.png`, `avatars/ohurteach-workspace-writer.png`, `avatars/ohurteach-workspace-reviewer.png`.
  Use original or licensed images: PNG or JPG, 512x512, at most 500KB each.
- Helper scripts for external tools are not bundled. The only bundled skill is the native rule pack `ohurteach-rulepack`.

## Install

Place this folder under `<WORKBUDDY_CONFIG_DIR>/plugins/marketplaces/my-experts/plugins/` and register it with the expert-manager registration script.
