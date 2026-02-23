"""Workflow generator utilities (diagram rendering)."""

from typing import Any, Dict, List


class WorkflowGenerator:
    """
    Generator that creates complete Intersight workflows from templates.
    
    Handles Mermaid diagram generation for workflow previews.
    """
    
    def __init__(self):
        """Initialize the workflow generator."""
        self.generated_workflows = []
    
    def generate_mermaid(self, workflow_json: List[Dict[str, Any]]) -> str:
        """
        Generate a Mermaid diagram for the workflow.
        
        Args:
            workflow_json: List of workflow components
            
        Returns:
            Mermaid diagram code as string
        """
        # Find workflow definitions in the components
        workflows = []
        tasks = {}
        
        for component in workflow_json:
            body = component.get("Body", {})
            obj_type = body.get("ObjectType", "")
            
            if obj_type == "workflow.WorkflowDefinition":
                workflows.append(body)
            elif obj_type == "workflow.TaskDefinition":
                tasks[body.get("Name", "")] = body
        
        if not workflows:
            return self._generate_component_diagram(workflow_json)
        
        # Generate diagram for the first (main) workflow
        return self._generate_workflow_diagram(workflows[0])
    
    def _generate_workflow_diagram(self, workflow: Dict[str, Any]) -> str:
        """Generate Mermaid diagram for a workflow definition."""
        lines = ["flowchart TB"]
        
        workflow_name = workflow.get("Name", "Workflow")
        lines.append(f"    subgraph {workflow_name}")
        
        tasks = workflow.get("Tasks", [])
        task_map = {t.get("Name"): t for t in tasks}
        
        # Define nodes
        for task in tasks:
            task_name = task.get("Name", "")
            task_type = task.get("ObjectType", "")
            label = task.get("Label", task_name)
            
            if task_type == "workflow.StartTask":
                lines.append(f'        {task_name}(["Start"])')
            elif task_type == "workflow.SuccessEndTask":
                lines.append(f'        {task_name}(["Success"])')
            elif task_type == "workflow.FailureEndTask":
                lines.append(f'        {task_name}(["Failure"])')
            elif task_type == "workflow.DecisionTask":
                lines.append(f'        {task_name}{{{{{label}}}}}')
            elif task_type == "workflow.WorkerTask":
                lines.append(f'        {task_name}["{label}"]')
            elif task_type == "workflow.SubWorkflowTask":
                lines.append(f'        {task_name}[["{label}"]]')
        
        # Define edges
        for task in tasks:
            task_name = task.get("Name", "")
            task_type = task.get("ObjectType", "")
            
            if task_type == "workflow.StartTask":
                next_task = task.get("NextTask")
                if next_task:
                    lines.append(f"        {task_name} --> {next_task}")
            
            elif task_type in ("workflow.WorkerTask", "workflow.SubWorkflowTask"):
                on_success = task.get("OnSuccess")
                on_failure = task.get("OnFailure")
                if on_success:
                    lines.append(f"        {task_name} -->|Success| {on_success}")
                if on_failure:
                    lines.append(f"        {task_name} -->|Failure| {on_failure}")
            
            elif task_type == "workflow.DecisionTask":
                for case in task.get("DecisionCases", []):
                    next_task = case.get("NextTask")
                    value = case.get("Value", "")
                    if next_task:
                        lines.append(f'        {task_name} -->|"{value}"| {next_task}')
                default_task = task.get("DefaultTask")
                if default_task:
                    lines.append(f'        {task_name} -->|Default| {default_task}')
        
        lines.append("    end")
        
        return "\n".join(lines)
    
    def _generate_component_diagram(self, components: List[Dict[str, Any]]) -> str:
        """Generate a simple component overview diagram."""
        lines = ["flowchart LR"]
        
        data_types = []
        tasks = []
        executors = []
        workflows = []
        
        for component in components:
            uri = component.get("Uri", "")
            name = component.get("Body", {}).get("Name", "Unknown")
            
            if "CustomDataTypeDefinitions" in uri:
                data_types.append(name)
            elif "TaskDefinitions" in uri:
                tasks.append(name)
            elif "BatchApiExecutors" in uri:
                executors.append(name)
            elif "WorkflowDefinitions" in uri:
                workflows.append(name)
        
        if data_types:
            lines.append("    subgraph DataTypes")
            for dt in data_types:
                safe_name = dt.replace(" ", "_").replace("-", "_")
                lines.append(f'        DT_{safe_name}["{dt}"]')
            lines.append("    end")
        
        if tasks:
            lines.append("    subgraph Tasks")
            for t in tasks:
                safe_name = t.replace(" ", "_").replace("-", "_")
                lines.append(f'        T_{safe_name}["{t}"]')
            lines.append("    end")
        
        if workflows:
            lines.append("    subgraph Workflows")
            for w in workflows:
                safe_name = w.replace(" ", "_").replace("-", "_")
                lines.append(f'        W_{safe_name}[["{w}"]]')
            lines.append("    end")
        
        # Add relationships
        if data_types and tasks:
            lines.append("    DataTypes --> Tasks")
        if tasks and workflows:
            lines.append("    Tasks --> Workflows")
        
        return "\n".join(lines)
    
