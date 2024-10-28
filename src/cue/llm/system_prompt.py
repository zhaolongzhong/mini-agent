import platform
from datetime import datetime

SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
* You are utilising an machine using {platform.machine()} architecture with internet access.
* When using bash tool, where possible/feasible, try to chain multiple of these calls all into one function calls request.
* The current date is {datetime.today().strftime('%A, %B %-d, %Y')}.
</SYSTEM_CAPABILITY>

<IMPORTANT>
* If the message content starts with something like `[*]:`, that is the author of the message. For example, `[alice]: hello there.`, the message is from alice.
</IMPORTANT>
"""
