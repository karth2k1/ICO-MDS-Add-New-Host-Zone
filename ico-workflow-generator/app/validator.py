"""Workflow validator for JSON schema and deep validation."""

import re
from typing import Any, Dict, List, Set


class WorkflowValidator:
    """
    Multi-layer validator for Intersight workflows.
    
    Validation layers:
    1. Schema validation - Required fields and types
    2. Reference validation - Task references exist
    3. Variable validation - Variable syntax is correct
    4. Semantic validation - Input/output compatibility
    """
    
    # Required fields for different object types
    REQUIRED_FIELDS = {
        "workflow.TaskDefinition": ["Name", "Label", "Description", "Properties", "ObjectType", "ClassId"],
        "workflow.WorkflowDefinition": ["Name", "Label", "Description", "Tasks", "ObjectType", "ClassId"],
        "workflow.BatchApiExecutor": ["Name", "Batch", "Output", "TaskDefinition", "ObjectType", "ClassId"],
        "workflow.CustomDataTypeDefinition": ["Name", "Label", "TypeDefinition", "ObjectType", "ClassId"],
        "bulk.RestSubRequest": ["Body", "Uri", "Verb", "ObjectType", "ClassId"]
    }
    
    # Valid task types within workflows
    VALID_TASK_TYPES = {
        "workflow.StartTask",
        "workflow.SuccessEndTask",
        "workflow.FailureEndTask",
        "workflow.WorkerTask",
        "workflow.SubWorkflowTask",
        "workflow.DecisionTask"
    }
    
    # Valid data types for inputs/outputs
    VALID_DATA_TYPES = {"string", "integer", "boolean", "json", "enum"}
    
    def __init__(self):
        """Initialize the validator."""
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate(self, workflow_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a complete workflow JSON.
        
        Args:
            workflow_json: List of bulk REST sub-requests
            
        Returns:
            Validation result with valid flag, errors, warnings, and info
        """
        self.errors = []
        self.warnings = []
        self.info = []
        
        if not workflow_json:
            self.errors.append("Workflow JSON is empty")
            return self._build_result()
        
        if not isinstance(workflow_json, list):
            self.errors.append("Workflow JSON must be an array of bulk requests")
            return self._build_result()
        
        # Track all defined names for reference validation
        defined_tasks = set()
        defined_workflows = set()
        defined_data_types = set()
        
        for i, component in enumerate(workflow_json):
            self._validate_bulk_request(component, i)
            
            body = component.get("Body", {})
            obj_type = body.get("ObjectType", "")
            name = body.get("Name", "")
            
            if obj_type == "workflow.TaskDefinition":
                defined_tasks.add(name)
                self._validate_task_definition(body, i)
            elif obj_type == "workflow.WorkflowDefinition":
                defined_workflows.add(name)
                self._validate_workflow_definition(body, i, defined_tasks)
            elif obj_type == "workflow.BatchApiExecutor":
                self._validate_batch_executor(body, i)
            elif obj_type == "workflow.CustomDataTypeDefinition":
                defined_data_types.add(name)
                self._validate_custom_data_type(body, i)
        
        # Cross-reference validation
        self._validate_cross_references(
            workflow_json, defined_tasks, defined_workflows, defined_data_types
        )
        
        return self._build_result()
    
    def _build_result(self) -> Dict[str, Any]:
        """Build the validation result dictionary."""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info
        }
    
    def _validate_bulk_request(self, request: Dict[str, Any], index: int):
        """Validate a bulk REST sub-request."""
        prefix = f"Component {index}"
        
        required = self.REQUIRED_FIELDS.get("bulk.RestSubRequest", [])
        for field in required:
            if field not in request:
                self.errors.append(f"{prefix}: Missing required field '{field}'")
        
        # Validate URI format
        uri = request.get("Uri", "")
        valid_uris = [
            "/v1/workflow/TaskDefinitions",
            "/v1/workflow/WorkflowDefinitions",
            "/v1/workflow/BatchApiExecutors",
            "/v1/workflow/CustomDataTypeDefinitions"
        ]
        if uri and uri not in valid_uris:
            self.warnings.append(f"{prefix}: Unusual URI '{uri}'")
        
        # Validate verb
        verb = request.get("Verb", "")
        if verb not in ("POST", "PATCH", "PUT"):
            self.warnings.append(f"{prefix}: Verb '{verb}' may not be suitable for import")
    
    def _validate_task_definition(self, task: Dict[str, Any], index: int):
        """Validate a task definition."""
        name = task.get("Name", f"Task {index}")
        prefix = f"Task '{name}'"
        
        # Check required fields
        required = self.REQUIRED_FIELDS.get("workflow.TaskDefinition", [])
        for field in required:
            if field not in task:
                self.errors.append(f"{prefix}: Missing required field '{field}'")
        
        # Validate properties
        props = task.get("Properties", {})
        if props:
            self._validate_input_definitions(props.get("InputDefinition", []), prefix)
            self._validate_output_definitions(props.get("OutputDefinition", []), prefix)
            
            # Check timeout
            timeout = props.get("Timeout", 0)
            if timeout < 60:
                self.warnings.append(f"{prefix}: Short timeout ({timeout}s) may cause failures")
            elif timeout > 3600:
                self.warnings.append(f"{prefix}: Long timeout ({timeout}s) may delay failure detection")
        
        # Validate tags
        tags = task.get("Tags", [])
        if not tags:
            self.info.append(f"{prefix}: No tags defined (recommended for organization)")
    
    def _validate_workflow_definition(
        self,
        workflow: Dict[str, Any],
        index: int,
        defined_tasks: Set[str]
    ):
        """Validate a workflow definition."""
        name = workflow.get("Name", f"Workflow {index}")
        prefix = f"Workflow '{name}'"
        
        # Check required fields
        required = self.REQUIRED_FIELDS.get("workflow.WorkflowDefinition", [])
        for field in required:
            if field not in workflow:
                self.errors.append(f"{prefix}: Missing required field '{field}'")
        
        # Validate tasks
        tasks = workflow.get("Tasks", [])
        if not tasks:
            self.errors.append(f"{prefix}: No tasks defined")
            return
        
        # Check for required task types
        task_types = {t.get("ObjectType") for t in tasks}
        
        if "workflow.StartTask" not in task_types:
            self.errors.append(f"{prefix}: Missing StartTask")
        
        if "workflow.SuccessEndTask" not in task_types:
            self.errors.append(f"{prefix}: Missing SuccessEndTask")
        
        # Build task name set for reference validation
        task_names = {t.get("Name") for t in tasks}
        
        for task in tasks:
            task_name = task.get("Name", "Unknown")
            task_type = task.get("ObjectType", "")
            
            if task_type not in self.VALID_TASK_TYPES:
                self.errors.append(f"{prefix}: Invalid task type '{task_type}' for task '{task_name}'")
            
            # Validate task references
            if task_type == "workflow.StartTask":
                next_task = task.get("NextTask")
                if next_task and next_task not in task_names:
                    self.errors.append(f"{prefix}: StartTask references non-existent task '{next_task}'")
            
            elif task_type == "workflow.WorkerTask":
                on_success = task.get("OnSuccess")
                on_failure = task.get("OnFailure")
                task_def_name = task.get("TaskDefinitionName", "")
                
                if on_success and on_success not in task_names:
                    self.errors.append(f"{prefix}: Task '{task_name}' OnSuccess references non-existent task '{on_success}'")
                if on_failure and on_failure not in task_names:
                    self.errors.append(f"{prefix}: Task '{task_name}' OnFailure references non-existent task '{on_failure}'")
                
                # Validate input parameters for variable syntax
                self._validate_input_parameters(task.get("InputParameters", {}), f"{prefix} task '{task_name}'")
            
            elif task_type == "workflow.SubWorkflowTask":
                workflow_def_name = task.get("WorkflowDefinitionName", "")
                if not workflow_def_name:
                    self.errors.append(f"{prefix}: SubWorkflowTask '{task_name}' missing WorkflowDefinitionName")
                
                self._validate_input_parameters(task.get("InputParameters", {}), f"{prefix} task '{task_name}'")
            
            elif task_type == "workflow.DecisionTask":
                for case in task.get("DecisionCases", []):
                    next_task = case.get("NextTask")
                    if next_task and next_task not in task_names:
                        self.errors.append(f"{prefix}: DecisionTask '{task_name}' references non-existent task '{next_task}'")
                
                default_task = task.get("DefaultTask")
                if default_task and default_task not in task_names:
                    self.errors.append(f"{prefix}: DecisionTask '{task_name}' DefaultTask references non-existent task '{default_task}'")
        
        # Validate input definitions
        self._validate_input_definitions(workflow.get("InputDefinition", []), prefix)
        
        # Validate output parameters
        self._validate_output_parameters(workflow.get("OutputParameters", {}), prefix)
        
        # Validate UI rendering data
        ui_data = workflow.get("UiRenderingData", {})
        if ui_data:
            positions = ui_data.get("Positions", [])
            positioned_tasks = {p.get("Name") for p in positions}
            for task in tasks:
                if task.get("Name") not in positioned_tasks:
                    self.warnings.append(f"{prefix}: Task '{task.get('Name')}' missing UI position")
    
    def _validate_batch_executor(self, executor: Dict[str, Any], index: int):
        """Validate a batch API executor."""
        name = executor.get("Name", f"Executor {index}")
        prefix = f"Executor '{name}'"
        
        # Check required fields
        required = self.REQUIRED_FIELDS.get("workflow.BatchApiExecutor", [])
        for field in required:
            if field not in executor:
                self.errors.append(f"{prefix}: Missing required field '{field}'")
        
        # Validate batch API calls
        batch = executor.get("Batch", [])
        if not batch:
            self.errors.append(f"{prefix}: No API calls defined in Batch")
        
        for i, api_call in enumerate(batch):
            api_name = api_call.get("Name", f"API {i}")
            method = api_call.get("Method", "")
            url = api_call.get("Url", "")
            
            if not method:
                self.errors.append(f"{prefix}: API call '{api_name}' missing Method")
            
            if not url:
                self.errors.append(f"{prefix}: API call '{api_name}' missing URL")
            
            # Validate Go template syntax in URL and Body
            self._validate_go_template_syntax(url, f"{prefix} API '{api_name}' URL")
            self._validate_go_template_syntax(api_call.get("Body", ""), f"{prefix} API '{api_name}' Body")
        
        # Validate output mappings
        output = executor.get("Output", {})
        for key, value in output.items():
            self._validate_go_template_syntax(value, f"{prefix} output '{key}'")
        
        # Validate task definition reference
        task_def = executor.get("TaskDefinition", {})
        selector = task_def.get("Selector", "")
        if not selector:
            self.warnings.append(f"{prefix}: TaskDefinition Selector is empty")
    
    def _validate_custom_data_type(self, data_type: Dict[str, Any], index: int):
        """Validate a custom data type definition."""
        name = data_type.get("Name", f"DataType {index}")
        prefix = f"DataType '{name}'"
        
        # Check required fields
        required = self.REQUIRED_FIELDS.get("workflow.CustomDataTypeDefinition", [])
        for field in required:
            if field not in data_type:
                self.errors.append(f"{prefix}: Missing required field '{field}'")
        
        # Validate type definition
        type_def = data_type.get("TypeDefinition", [])
        if not type_def:
            self.errors.append(f"{prefix}: Empty TypeDefinition")
    
    def _validate_input_definitions(self, inputs: List[Dict[str, Any]], prefix: str):
        """Validate input definitions."""
        input_names = set()
        
        for inp in inputs:
            name = inp.get("Name", "")
            
            if not name:
                self.errors.append(f"{prefix}: Input definition missing Name")
                continue
            
            if name in input_names:
                self.errors.append(f"{prefix}: Duplicate input name '{name}'")
            input_names.add(name)
            
            if not inp.get("Label"):
                self.warnings.append(f"{prefix}: Input '{name}' missing Label")
            
            # Validate data type
            props = inp.get("Properties", {})
            if props:
                data_type = props.get("Type", "")
                if data_type and data_type not in self.VALID_DATA_TYPES:
                    self.warnings.append(f"{prefix}: Input '{name}' has unusual type '{data_type}'")
    
    def _validate_output_definitions(self, outputs: List[Dict[str, Any]], prefix: str):
        """Validate output definitions."""
        output_names = set()
        
        for out in outputs:
            name = out.get("Name", "")
            
            if not name:
                self.errors.append(f"{prefix}: Output definition missing Name")
                continue
            
            if name in output_names:
                self.errors.append(f"{prefix}: Duplicate output name '{name}'")
            output_names.add(name)
    
    def _validate_input_parameters(self, params: Dict[str, str], prefix: str):
        """Validate input parameters for variable syntax."""
        for key, value in params.items():
            if isinstance(value, str) and "${" in value:
                # Validate Intersight variable syntax
                if not re.search(r'\$\{[\w.]+\}', value):
                    self.warnings.append(f"{prefix}: Parameter '{key}' may have invalid variable syntax")
    
    def _validate_output_parameters(self, params: Dict[str, str], prefix: str):
        """Validate output parameters."""
        for key, value in params.items():
            if isinstance(value, str) and "${" in value:
                # Should reference a task output
                if not re.search(r'\$\{[\w.]+\.output\.[\w.]+\}', value):
                    self.warnings.append(f"{prefix}: Output parameter '{key}' may have invalid format")
    
    def _validate_go_template_syntax(self, template: str, context: str):
        """Validate Go template syntax."""
        if not template or not isinstance(template, str):
            return
        
        # Check for unmatched braces
        open_count = template.count("{{")
        close_count = template.count("}}")
        
        if open_count != close_count:
            self.errors.append(f"{context}: Unmatched Go template braces ({{ {open_count}, }} {close_count})")
        
        # Check for common template patterns
        if "{{" in template:
            # Validate .global references
            if ".global." in template and not re.search(r'\{\{[\s.]*\.global\.[\w.]+', template):
                self.warnings.append(f"{context}: Possible invalid .global template reference")
    
    def _validate_cross_references(
        self,
        workflow_json: List[Dict[str, Any]],
        defined_tasks: Set[str],
        defined_workflows: Set[str],
        defined_data_types: Set[str]
    ):
        """Validate cross-references between components."""
        for component in workflow_json:
            body = component.get("Body", {})
            obj_type = body.get("ObjectType", "")
            name = body.get("Name", "Unknown")
            
            if obj_type == "workflow.WorkflowDefinition":
                # Check that referenced tasks exist
                for task in body.get("Tasks", []):
                    if task.get("ObjectType") == "workflow.WorkerTask":
                        task_def_name = task.get("TaskDefinitionName", "")
                        if task_def_name and task_def_name not in defined_tasks:
                            # This is only a warning since the task might exist in Intersight
                            self.info.append(
                                f"Workflow '{name}': References task '{task_def_name}' "
                                "which is not defined in this import (may exist in Intersight)"
                            )
            
            elif obj_type == "workflow.BatchApiExecutor":
                # Check that the task definition exists
                task_def = body.get("TaskDefinition", {})
                selector = task_def.get("Selector", "")
                # Extract task name from selector
                match = re.search(r"Name eq ['\"]([^'\"]+)['\"]", selector)
                if match:
                    referenced_task = match.group(1)
                    if referenced_task not in defined_tasks:
                        self.warnings.append(
                            f"Executor '{name}': References task '{referenced_task}' "
                            "which should be defined before the executor"
                        )
        
        self.info.append(f"Found {len(defined_tasks)} task definitions")
        self.info.append(f"Found {len(defined_workflows)} workflow definitions")
        self.info.append(f"Found {len(defined_data_types)} custom data type definitions")
