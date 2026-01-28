"""Workflow generator that assembles templates with parameter substitution."""

import importlib
from typing import Any, Dict, List, Optional


class WorkflowGenerator:
    """
    Generator that creates complete Intersight workflows from templates.
    
    Handles:
    - Loading template modules
    - Parameter substitution
    - Workflow assembly
    - Mermaid diagram generation
    """
    
    def __init__(self):
        """Initialize the workflow generator."""
        self.generated_workflows = []
    
    def generate(
        self,
        matched_templates: List[Dict[str, Any]],
        requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate workflow JSON from matched templates.
        
        Args:
            matched_templates: List of matched templates from rule engine
            requirements: Parsed requirements with parameters
            
        Returns:
            List of bulk REST sub-requests ready for import
        """
        all_components = []
        seen_names = set()  # Track to avoid duplicates
        
        for template in matched_templates:
            try:
                # Import the template module
                module = importlib.import_module(template["module"])
                
                # Extract parameters from requirements
                params = self._extract_params(template, requirements)
                
                # Generate the workflow components
                if hasattr(module, "generate_full_workflow"):
                    components = module.generate_full_workflow(params)
                    
                    # Add components, avoiding duplicates
                    for component in components:
                        name = component.get("Body", {}).get("Name", "")
                        if name and name not in seen_names:
                            all_components.append(component)
                            seen_names.add(name)
                            
            except ImportError as e:
                print(f"Failed to import template {template['module']}: {e}")
                continue
            except Exception as e:
                print(f"Error generating workflow from {template['name']}: {e}")
                continue
        
        self.generated_workflows = all_components
        return all_components
    
    def _extract_params(
        self,
        template: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract parameters from requirements for template generation.
        
        Args:
            template: Template configuration
            requirements: Parsed requirements
            
        Returns:
            Dictionary of parameters for the template
        """
        params = {}
        req_params = requirements.get("parameters", {})
        
        # Map extracted parameters to template parameters
        if req_params.get("zone_names"):
            params["zone_name"] = req_params["zone_names"][0]
        
        if req_params.get("wwpns"):
            params["wwpns"] = req_params["wwpns"]
        
        if req_params.get("vsan_ids"):
            params["vsan_ids"] = req_params["vsan_ids"]
        
        if req_params.get("vlan_ids"):
            params["vlan_ids"] = req_params["vlan_ids"]
        
        if req_params.get("hostnames"):
            params["hostnames"] = req_params["hostnames"]
        
        if req_params.get("fabrics"):
            # Check if both fabrics are mentioned
            fabrics = [f.upper() for f in req_params["fabrics"]]
            params["use_fabric_b"] = "B" in fabrics
        
        return params
    
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
    
    def generate_task_only(
        self,
        template_name: str,
        params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate only task definitions without a wrapper workflow.
        
        Args:
            template_name: Name of the template
            params: Parameters for customization
            
        Returns:
            List of task definition bulk requests
        """
        from app.rule_engine import RuleEngine
        
        rule_engine = RuleEngine()
        template = rule_engine.get_template_by_name(template_name)
        
        if not template:
            return []
        
        try:
            module = importlib.import_module(template["module"])
            
            if hasattr(module, "get_task_definitions"):
                tasks = module.get_task_definitions()
                from app.models import create_bulk_request
                return [
                    create_bulk_request(t, "/v1/workflow/TaskDefinitions")
                    for t in tasks
                ]
        except ImportError:
            pass
        
        return []
