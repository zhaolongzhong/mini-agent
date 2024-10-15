from enum import Enum


class Tool(Enum):
    FileRead = "read_file"
    FileWrite = "write_to_file"
    CheckFolder = "scan_folder"
    CodeInterpreter = "run_python_script"
    ShellTool = "execute_shell_command"
    MakePlan = "make_plan"
    BrowseWeb = "browse_web"
    ManageEmail = "manage_email"
    ManageDrive = "manage_drive"
