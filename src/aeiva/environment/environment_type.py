class EnvironmentType:
    """
    A class to hold constants for various environment types, organized by broad categories
    to maximize generality while supporting diverse use cases.
    
    Categories:
        - Interaction-Based: Environments with user or agent interaction.
        - Digital: Environments involving digital interfaces, applications, or software systems.
        - Data-Based: Static or dynamic data collections or document repositories.
        - Virtual/Simulated: Simulated, spatial, or immersive virtual environments.
        - World-Level: Comprehensive real or virtual world environments.
    """

    # Interaction-Based Environments
    INTERACTIVE = "Interactive"  # Environments involving user or multi-agent interaction.

    # Digital Environments
    DIGITAL_ENVIRONMENT = "Digital Environment"  # Digital workspaces, applications, OS, or software systems.

    # Data-Based Environments
    DATA_REPOSITORY = "Data Repository"  # Static datasets, dynamic data streams, or document repositories (e.g., knowledge bases).

    # Virtual/Simulated Environments
    VIRTUAL_ENVIRONMENT = "Virtual Environment"  # Simulated or immersive 3D spaces, including games and VR.

    # World-Level Environments
    FULL_WORLD = "Full World"  # Comprehensive virtual or real-world environment.

    # Meta/Complex Environments
    HYBRID_ENVIRONMENT = "Hybrid Environment"  # Combination of multiple types.
    
    # Custom environment type for unique or unspecified cases.
    CUSTOM = "Custom"