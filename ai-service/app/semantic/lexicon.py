DOMAINS = {
    "physics": [
        "quantum", "qubit", "entanglement", "superposition", "photon", "energy", "mass", "force",
        "velocity", "acceleration", "gravity", "relativity", "electromagnet", "entropy", "wavefunction",
        "electron", "momentum", "particle", "thermodynamics", "newton", "schrodinger", "heisenberg",
        "lorentz", "kelvin", "joule", "watt", "ohm", "volt", "magnetic", "electric field", "neutrino",
        "dark matter", "big bang", "black hole", "wave", "frequency", "wavelength", "amplitude",
        "inertia", "friction", "pressure", "density", "plasma", "quantum computing",
    ],
    "mathematics": [
        "matrix", "vector", "integral", "derivative", "calculus", "theorem", "equation", "polynomial",
        "logarithm", "fraction", "geometry", "topology", "algebra", "probability", "statistics",
        "function", "limit", "series", "manifold", "eigenvalue", "linear", "differential", "integer",
        "rational", "prime", "combinatorics", "graph theory", "group theory", "axiom", "proof",
        "differential equation", "trigonometry", "sine", "cosine", "tangent", "hyperbola", "parabola",
        "fibonacci", "pythagoras", "euclid", "gauss", "euler", "riemann",
    ],
    "programming": [
        "algorithm", "function", "class", "loop", "variable", "array", "object", "api", "database",
        "compiler", "debug", "recursion", "data structure", "sorting", "binary", "hash", "stack",
        "queue", "python", "javascript", "typescript", "rust", "java", "sql", "html", "css", "golang",
        "swift", "kotlin", "react", "vue", "node", "django", "flask", "backend", "frontend", "syntax",
        "repository", "commit", "pull request", "framework", "library", "package", "dependency",
        "garbage collector", "memory", "thread", "process", "asynchronous", "promise", "async",
        "monorepo", "microservice", "container", "docker", "kubernetes", "deployment", "endpoint",
    ],
    "chemistry": [
        "molecule", "atom", "bond", "reaction", "compound", "element", "stoichiometry", "catalyst",
        "acid", "base", "oxidation", "reduction", "molar", "ion", "solution", "periodic", "ph",
        "enthalpy", "entropy of reaction", "covalent", "ionic", "electron shell", "orbitals",
        "mole", "reactant", "product", "precipitate", "buffer", "titration",
    ],
    "biology": [
        "cell", "dna", "gene", "protein", "organism", "evolution", "ecosystem", "photosynthesis",
        "enzyme", "mitosis", "meiosis", "chromosome", "bacteria", "virus", "neuron", "homeostasis",
        "rna", "mutation", "natural selection", "symbiosis", "metabolism", "respiration", "biome",
        "predator", "prey", "fossil", "genome", "dna sequencing", "polymerase",
    ],
    "economics": [
        "market", "supply", "demand", "inflation", "gdp", "revenue", "profit", "elasticity",
        "monopoly", "fiscal", "monetary", "investment", "capital", "trade", "currency", "interest",
        "interest rate", "unemployment", "inflation rate", "gross domestic product", "export",
        "import", "subsidy", "tariff", "liquidity", "asset", "liability", "dividend", "stock",
        "bond market", "aggregate demand",
    ],
    "philosophy": [
        "logic", "argument", "ethics", "ontology", "metaphysics", "epistemology", "consciousness",
        "free will", "rationalism", "empiricism", "syllogism", "paradox", "moral", "virtue",
        "utilitarianism", "deontology", "existentialism", "phenomenology", "determinism", "truth",
        "knowledge", "belief", "causality", "aesthetics",
    ],
    "history": [
        "empire", "revolution", "war", "dynasty", "civilization", "treaty", "colonialism",
        "renaissance", "medieval", "ancient", "industrial", "monarchy", "republic", "feudalism",
        "enlightenment", "cold war", "wwi", "wwii", "roman", "greek", "ottoman", "byzantine",
        "migration", "archaeology", "manuscript", "artifact",
    ],
    "computer-science": [
        "complexity", "big-o", "np", "automata", "turing", "compilation", "lambda", "category theory",
        "monad", "functor", "type system", "semantics", "formal language", "regular expression",
        "context-free", "state machine", "finite automaton", "halting problem", "p vs np",
        "distributed systems", "concurrency", "protocol", "latency", "throughput", "consensus",
        "blockchain", "cryptography", "encryption", "hash function",
    ],
}

KNOWN_TERMS = sorted({term for terms in DOMAINS.values() for term in terms})

STOP_CAPS = {
    "The", "A", "An", "This", "That", "These", "Those", "It", "I", "You", "We", "They", "He",
    "She", "My", "Your", "Our", "Their", "And", "Or", "But", "If", "Then", "Else", "For", "While",
    "When", "Why", "How", "What", "Where", "Who", "Which", "Not", "In", "On", "At", "To", "From",
    "With", "By", "Of", "As", "Are", "Is", "Was", "Were", "Be", "Been", "Being", "Do", "Does",
    "Did", "Will", "Would", "Can", "Could", "Should", "Shall", "May", "Might", "Must", "Yes", "No",
    "One", "Two", "Three", "Today", "Tomorrow", "Yesterday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday", "January", "February", "March", "April", "June",
    "July", "August", "September", "October", "November", "December", "So", "Yet", "Nor", "Both",
    "Each", "Every", "Some", "Any", "All", "Both", "None", "Nothing", "Everything",
}

CODE_LANGUAGES = {
    "python", "javascript", "typescript", "rust", "java", "c", "cpp", "csharp", "go", "sql",
    "bash", "html", "css", "json", "ruby", "php", "swift", "kotlin", "unknown",
}
