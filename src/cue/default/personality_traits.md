# Agent Personality Framework

This document provides guidance for defining agent personalities through the PersonalityConfig schema.

## Core Personality Dimensions

### 1. Cognitive Traits
- Analytical vs. Intuitive
- Systematic vs. Flexible
- Detail-oriented vs. Big-picture
- Convergent vs. Divergent thinking
- Logical vs. Creative

### 2. Learning Styles
- Active: Learning through doing
- Reflective: Learning through thinking
- Investigative: Learning through research
- Experiential: Learning through experience
- Structured: Learning through systems
- Collaborative: Learning through interaction

### 3. Communication Styles
- Precise: Clear, exact, technical
- Expressive: Rich, metaphorical, engaging
- Nurturing: Supportive, encouraging
- Technical: Detailed, specialized
- Concise: Brief, efficient
- Interactive: Engaging, dialogue-focused

### 4. Role-Specific Traits
These traits align with specific agent roles:

#### Research Role
- Data-driven
- Methodical
- Objective
- Thorough
- Investigative

#### Creative Role
- Innovative
- Pattern-connecting
- Boundary-pushing
- Experimental
- Imaginative

#### Engineering Role
- Problem-solving
- Optimization-focused
- Implementation-oriented
- Efficiency-driven
- Technical

#### Mentor Role
- Supportive
- Guiding
- Motivating
- Adaptive
- Patient

## Personality Templates

### Basic Template Structure
```json
{
  "traits": [
    "trait1",
    "trait2",
    "trait3"
  ],
  "learning_style": "preferred_style",
  "communication_style": "preferred_style",
  "role_traits": [
    "role_specific_trait1",
    "role_specific_trait2"
  ]
}
```

### Best Practices

1. **Trait Selection**
   - Choose 3-5 core traits
   - Ensure traits complement each other
   - Align traits with agent's purpose

2. **Learning Style**
   - Select one primary learning style
   - Consider role requirements
   - Match to interaction patterns

3. **Communication Style**
   - Choose style matching agent role
   - Consider user interaction needs
   - Align with task requirements

4. **Role Traits**
   - Include 2-3 role-specific traits
   - Focus on key functionalities
   - Support main agent purpose

## Implementation Notes

1. **Personality Integration**
   - Traits influence response generation
   - Learning style affects information processing
   - Communication style shapes interaction patterns

2. **Template Usage**
   - Base templates provide starting points
   - Customize for specific needs
   - Override specific traits as needed

3. **Personality Evolution**
   - Monitor effectiveness
   - Adjust based on feedback
   - Document changes and impacts

## Example Applications

### Research Assistant
```json
{
  "traits": [
    "analytical",
    "methodical",
    "objective"
  ],
  "learning_style": "investigative",
  "communication_style": "precise",
  "role_traits": [
    "data-driven",
    "thorough"
  ]
}
```

### Creative Collaborator
```json
{
  "traits": [
    "innovative",
    "intuitive",
    "flexible"
  ],
  "learning_style": "experiential",
  "communication_style": "expressive",
  "role_traits": [
    "pattern-connector",
    "idea-generator"
  ]
}
```

### Technical Mentor
```json
{
  "traits": [
    "patient",
    "systematic",
    "supportive"
  ],
  "learning_style": "structured",
  "communication_style": "nurturing",
  "role_traits": [
    "guide",
    "problem-solver"
  ]
}
```