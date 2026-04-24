# AgentOps Firewall Policies V0

## Policy Table

| Tool | Risk | Auto allowed | Approval | V1 status |
| --- | --- | --- | --- | --- |
| create_folder | low | yes | no | enabled |
| create_file | low | yes | no | enabled |
| prepare_email_draft | medium | no | yes | enabled as draft |
| send_email | high | no | yes | disabled |
| browser_submit_form | high | no | yes | disabled |
| run_shell_command | critical | no | yes | disabled |
| modify_code | critical | no | yes | disabled |

## Path Policy

`create_folder` and `create_file` are limited to:

```text
./data/generated_projects
```

Any path outside that directory is blocked.

## Disabled Action Rule

The following tools are blocked in v1 regardless of approval or input:

- send_email;
- browser_submit_form;
- run_shell_command;
- modify_code.

## Medium Impact Rule

`prepare_email_draft` is allowed only as a draft workflow and always requires user approval before execution in later sprints.

## Unknown Tool Rule

Unknown tools default to critical risk and blocked.

