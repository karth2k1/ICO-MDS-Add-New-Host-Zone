"""Rule engine for matching JIRA requirements to workflow templates."""

import os
import re
import importlib
from typing import Any, Dict, List, Optional, Tuple

import yaml


class RuleEngine:
    """
    Rule-based engine for matching requirements to workflow templates.
    
    Uses YAML configuration to define:
    - Pattern matching rules (regex)
    - Keyword matching
    - Required keyword combinations
    - Action type mappings
    """
    
    def __init__(self, rules_path: str = None):
        """
        Initialize the rule engine.
        
        Args:
            rules_path: Path to the rules YAML file. Defaults to rules/mappings.yaml
        """
        if rules_path is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            rules_path = os.path.join(base_dir, "rules", "mappings.yaml")
        
        self.rules_path = rules_path
        self.rules = self._load_rules()
        self.scoring = self.rules.get("scoring", {
            "pattern_match": 50,
            "keyword_match": 10,
            "required_match": 30,
            "action_match": 40
        })
    
    def _load_rules(self) -> Dict[str, Any]:
        """Load rules from YAML configuration."""
        try:
            with open(self.rules_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Return default rules if file not found
            return self._get_default_rules()
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """Get default rules if configuration file is missing."""
        return {
            "templates": [
                {
                    "name": "add_host_to_san",
                    "module": "workflow_templates.mds.add_host_to_san",
                    "patterns": ["add.*host.*san", "zone.*host"],
                    "keywords": ["add", "host", "san", "zone", "fabric"],
                    "required_keywords": [["host", "zone"], ["san", "add"]],
                    "priority": 100,
                    "category": "MDS"
                },
                {
                    "name": "toggle_locator_led",
                    "module": "workflow_templates.compute.toggle_locator_led",
                    "patterns": ["toggle.*led", "locator.*led"],
                    "keywords": ["toggle", "led", "locator"],
                    "required_keywords": [["led"]],
                    "priority": 90,
                    "category": "Compute"
                },
                {
                    "name": "get_server_inventory",
                    "module": "workflow_templates.compute.get_server_inventory",
                    "patterns": ["get.*inventory", "list.*server"],
                    "keywords": ["inventory", "list", "server"],
                    "required_keywords": [["inventory"]],
                    "priority": 70,
                    "category": "Compute"
                }
            ],
            "action_mappings": {
                "add_host_to_san": "add_host_to_san",
                "toggle_led": "toggle_locator_led",
                "get_inventory": "get_server_inventory"
            },
            "scoring": {
                "pattern_match": 50,
                "keyword_match": 10,
                "required_match": 30,
                "action_match": 40
            }
        }
    
    def match(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Match requirements to workflow templates.
        
        Args:
            requirements: Parsed requirements from JIRA text containing:
                - raw_text: Original text
                - keywords: Extracted keywords
                - actions: Identified actions
                - parameters: Extracted parameters
                
        Returns:
            List of matched templates with scores, sorted by score descending
        """
        raw_text = requirements.get("raw_text", "").lower()
        keywords = set(kw.lower() for kw in requirements.get("keywords", []))
        actions = requirements.get("actions", [])
        
        matches = []
        
        for template in self.rules.get("templates", []):
            score, match_details = self._score_template(
                template, raw_text, keywords, actions
            )
            
            if score > 0:
                matches.append({
                    "name": template["name"],
                    "module": template["module"],
                    "category": template.get("category", "Unknown"),
                    "priority": template.get("priority", 0),
                    "score": score,
                    "match_details": match_details
                })
        
        # Sort by score (descending), then by priority (descending)
        matches.sort(key=lambda x: (x["score"], x["priority"]), reverse=True)
        
        return matches
    
    def _score_template(
        self,
        template: Dict[str, Any],
        text: str,
        keywords: set,
        actions: List[Dict[str, str]]
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate match score for a template.
        
        Returns:
            Tuple of (score, match_details)
        """
        score = 0
        match_details = {
            "patterns_matched": [],
            "keywords_matched": [],
            "required_matched": False,
            "actions_matched": []
        }
        
        # Check pattern matches
        for pattern in template.get("patterns", []):
            if re.search(pattern, text, re.IGNORECASE):
                score += self.scoring["pattern_match"]
                match_details["patterns_matched"].append(pattern)
        
        # Check keyword matches
        template_keywords = set(kw.lower() for kw in template.get("keywords", []))
        matched_keywords = keywords.intersection(template_keywords)
        for kw in matched_keywords:
            score += self.scoring["keyword_match"]
            match_details["keywords_matched"].append(kw)
        
        # Check required keyword combinations
        required_groups = template.get("required_keywords", [])
        for group in required_groups:
            group_set = set(kw.lower() for kw in group)
            if group_set.issubset(keywords) or any(
                re.search(r"\b" + kw + r"\b", text, re.IGNORECASE) 
                for kw in group
            ):
                score += self.scoring["required_match"]
                match_details["required_matched"] = True
                break
        
        # Check action type mappings
        action_mappings = self.rules.get("action_mappings", {})
        for action in actions:
            action_type = action.get("type", "")
            if action_mappings.get(action_type) == template["name"]:
                score += self.scoring["action_match"]
                match_details["actions_matched"].append(action_type)
        
        return score, match_details
    
    def get_template_module(self, template_name: str) -> Optional[Any]:
        """
        Get the Python module for a template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Imported module or None if not found
        """
        for template in self.rules.get("templates", []):
            if template["name"] == template_name:
                try:
                    return importlib.import_module(template["module"])
                except ImportError as e:
                    print(f"Failed to import template module {template['module']}: {e}")
                    return None
        return None
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all available workflow templates.
        
        Returns:
            List of template metadata
        """
        templates = []
        
        for template in self.rules.get("templates", []):
            template_info = {
                "name": template["name"],
                "category": template.get("category", "Unknown"),
                "keywords": template.get("keywords", []),
                "priority": template.get("priority", 0)
            }
            
            # Try to get additional metadata from the module
            try:
                module = importlib.import_module(template["module"])
                if hasattr(module, "TEMPLATE_METADATA"):
                    metadata = module.TEMPLATE_METADATA
                    template_info.update({
                        "label": metadata.get("label", template["name"]),
                        "description": metadata.get("description", ""),
                        "parameters": metadata.get("parameters", [])
                    })
            except ImportError:
                template_info["label"] = template["name"]
                template_info["description"] = "Template module not found"
            
            templates.append(template_info)
        
        return templates
    
    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get template configuration by name."""
        for template in self.rules.get("templates", []):
            if template["name"] == name:
                return template
        return None
