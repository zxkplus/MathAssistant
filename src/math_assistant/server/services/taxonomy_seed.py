"""Default math knowledge point taxonomy.

Provides ~70 knowledge points organized as a 3-level hierarchy.
Call seed_taxonomy(db) to populate the database idempotently.
"""

from sqlalchemy.orm import Session

from math_assistant.server.models.knowledge_point import KnowledgePoint

# Hierarchy definition: (name, description, importance, [prerequisite_names])
# Top-level entries with no parent create root nodes under "Math".
TAXONOMY: dict[str, list[tuple[str, str, float, list[str] | None]]] = {
    "Arithmetic": [
        ("Basic Operations", "Addition, subtraction, multiplication, division", 1.0, None),
        ("Fractions and Decimals", "Operations with fractions and decimal numbers", 0.9, ["Basic Operations"]),
        ("Percentages", "Percentage calculations and applications", 0.8, ["Fractions and Decimals"]),
        ("Factors and Multiples", "Prime factorization, GCD, LCM", 0.7, ["Basic Operations"]),
        ("Exponents and Roots", "Powers, square roots, scientific notation", 0.8, ["Basic Operations"]),
    ],
    "Algebra": [
        ("Linear Equations", "Solving equations of the form ax + b = c", 1.0, None),
        ("Quadratic Equations", "Solving ax² + bx + c = 0, factoring, quadratic formula", 0.95, ["Linear Equations"]),
        ("Polynomials", "Polynomial operations, factoring, and theorems", 0.9, ["Linear Equations"]),
        ("Inequalities", "Solving and graphing linear and nonlinear inequalities", 0.85, ["Linear Equations"]),
        ("Systems of Equations", "Solving multiple equations simultaneously", 0.9, ["Linear Equations"]),
        ("Functions and Graphs", "Function notation, domain/range, graphing", 0.95, ["Linear Equations"]),
        ("Exponents and Logarithms", "Exponential and logarithmic functions and equations", 0.85, ["Functions and Graphs"]),
        ("Rational Expressions", "Simplifying and solving rational equations", 0.7, ["Polynomials"]),
        ("Sequences and Series", "Arithmetic and geometric sequences, summation", 0.75, ["Functions and Graphs"]),
        ("Complex Numbers", "Operations with complex numbers, polar form", 0.6, ["Quadratic Equations"]),
    ],
    "Geometry": [
        ("Lines and Angles", "Parallel lines, transversals, angle relationships", 1.0, None),
        ("Triangles", "Triangle properties, congruence, similarity", 1.0, ["Lines and Angles"]),
        ("Circles", "Circle properties, arcs, chords, tangents", 0.9, ["Lines and Angles"]),
        ("Polygons", "Properties of quadrilaterals and other polygons", 0.85, ["Triangles"]),
        ("Area and Perimeter", "Computing area and perimeter of 2D shapes", 0.95, ["Triangles", "Polygons"]),
        ("Volume and Surface Area", "3D shapes: prisms, cylinders, spheres, cones", 0.9, ["Area and Perimeter"]),
        ("Coordinate Geometry", "Points, lines, and shapes on the coordinate plane", 0.9, ["Lines and Angles"]),
        ("Transformations", "Translations, rotations, reflections, dilations", 0.75, ["Coordinate Geometry"]),
        ("Geometric Proofs", "Deductive reasoning and formal proof writing", 0.7, ["Triangles", "Circles"]),
    ],
    "Trigonometry": [
        ("Sine, Cosine, Tangent", "Basic trigonometric ratios in right triangles", 0.95, None),
        ("Unit Circle", "Trigonometric functions on the unit circle, radians", 0.9, ["Sine, Cosine, Tangent"]),
        ("Trigonometric Identities", "Pythagorean, reciprocal, double-angle identities", 0.85, ["Unit Circle"]),
        ("Trigonometric Equations", "Solving equations involving trig functions", 0.8, ["Trigonometric Identities"]),
        ("Law of Sines and Cosines", "Solving non-right triangles", 0.85, ["Sine, Cosine, Tangent"]),
        ("Graphs of Trig Functions", "Graphing sine, cosine, tangent and transformations", 0.8, ["Unit Circle"]),
    ],
    "Calculus": [
        ("Limits and Continuity", "Limit definition, continuity, asymptotes", 1.0, None),
        ("Derivatives", "Definition of derivative, tangent lines, rates of change", 1.0, ["Limits and Continuity"]),
        ("Derivative Rules", "Power, product, quotient, chain rules", 0.95, ["Derivatives"]),
        ("Applications of Derivatives", "Optimization, related rates, curve sketching", 0.9, ["Derivative Rules"]),
        ("Integrals", "Indefinite and definite integrals, area under curve", 1.0, ["Derivatives"]),
        ("Integration Techniques", "Substitution, parts, partial fractions, trig substitution", 0.9, ["Integrals"]),
        ("Applications of Integrals", "Area, volume, arc length, work, average value", 0.85, ["Integration Techniques"]),
        ("Differential Equations", "First-order ODEs, separable equations, modeling", 0.8, ["Integrals", "Derivatives"]),
        ("Multivariable Calculus", "Partial derivatives, multiple integrals, vector calculus", 0.6, ["Applications of Derivatives", "Applications of Integrals"]),
        ("Sequences and Series (Calc)", "Convergence tests, Taylor and Maclaurin series", 0.65, ["Limits and Continuity"]),
    ],
    "Probability and Statistics": [
        ("Counting Principles", "Permutations, combinations, fundamental counting principle", 0.9, None),
        ("Probability Rules", "Addition rule, multiplication rule, conditional probability", 0.95, ["Counting Principles"]),
        ("Random Variables", "Discrete and continuous random variables, expectation", 0.85, ["Probability Rules"]),
        ("Statistical Measures", "Mean, median, mode, variance, standard deviation", 0.9, None),
        ("Distributions", "Binomial, normal, Poisson distributions", 0.8, ["Random Variables"]),
        ("Hypothesis Testing", "Null/alternative hypotheses, p-values, significance", 0.7, ["Distributions"]),
        ("Regression and Correlation", "Linear regression, correlation coefficient", 0.75, ["Statistical Measures"]),
        ("Data Visualization", "Histograms, box plots, scatter plots, interpretation", 0.8, ["Statistical Measures"]),
    ],
    "Linear Algebra": [
        ("Vectors", "Vector operations, dot product, cross product", 0.9, None),
        ("Matrices", "Matrix operations, multiplication, transpose", 0.95, ["Vectors"]),
        ("Determinants", "Computing determinants, properties, Cramer's rule", 0.8, ["Matrices"]),
        ("Eigenvalues and Eigenvectors", "Characteristic polynomial, diagonalization", 0.7, ["Matrices", "Determinants"]),
        ("Linear Transformations", "Matrix representations, kernel, range", 0.7, ["Matrices"]),
        ("Systems of Linear Equations", "Gaussian elimination, rank, solutions", 0.9, ["Matrices"]),
    ],
    "Number Theory": [
        ("Prime Numbers", "Prime factorization, primality testing", 0.8, None),
        ("Divisibility", "Divisibility rules, Euclidean algorithm", 0.9, None),
        ("Modular Arithmetic", "Congruences, modular inverses, applications", 0.75, ["Divisibility"]),
        ("Diophantine Equations", "Integer solutions to polynomial equations", 0.5, ["Modular Arithmetic"]),
    ],
    "Discrete Mathematics": [
        ("Logic and Proofs", "Propositional logic, proof techniques, quantifiers", 0.85, None),
        ("Set Theory", "Sets, Venn diagrams, operations, cardinality", 0.9, None),
        ("Combinatorics", "Counting, pigeonhole principle, inclusion-exclusion", 0.75, ["Counting Principles"]),
        ("Graph Theory", "Graphs, trees, paths, connectivity, coloring", 0.65, ["Set Theory"]),
        ("Recurrence Relations", "Solving recurrences, generating functions", 0.55, ["Sequences and Series"]),
    ],
}


def seed_taxonomy(db: Session) -> dict[str, int]:
    """Seed the database with the default math knowledge point taxonomy.

    Idempotent: skips entries that already exist (matched by full_path).

    Args:
        db: SQLAlchemy database session.

    Returns:
        Dict with 'created' and 'skipped' counts.
    """
    created = 0
    skipped = 0

    for category, topics in TAXONOMY.items():
        # Create or get the category (depth=0)
        cat_kp = _get_or_create_kp(
            db, name=category, parent_id=None, depth=0,
            full_path=category, description=f"Topics in {category.lower()}",
            importance=1.0,
        )
        if cat_kp is True:
            created += 1
        elif cat_kp is False:
            skipped += 1
        # cat_kp could be the KP object if it already existed

        # Get the actual KP object for parent reference
        cat_obj = db.query(KnowledgePoint).filter_by(full_path=category).first()

        for name, desc, importance, _prereqs in topics:
            full_path = f"{category} > {name}"
            prereq_ids = None
            if _prereqs:
                prereq_ids = []
                for prereq_name in _prereqs:
                    prereq_full = f"{category} > {prereq_name}"
                    prereq_kp = db.query(KnowledgePoint).filter_by(
                        full_path=prereq_full
                    ).first()
                    if prereq_kp:
                        prereq_ids.append(prereq_kp.id)

            result = _get_or_create_kp(
                db,
                name=name,
                parent_id=cat_obj.id,
                depth=1,
                full_path=full_path,
                description=desc,
                importance=importance,
                prerequisite_ids=prereq_ids if prereq_ids else None,
            )
            if result is True:
                created += 1
            elif result is False:
                skipped += 1

    db.commit()
    return {"created": created, "skipped": skipped}


def _get_or_create_kp(
    db: Session,
    name: str,
    parent_id: int | None,
    depth: int,
    full_path: str,
    description: str,
    importance: float,
    prerequisite_ids: list[int] | None = None,
) -> bool | KnowledgePoint:
    """Create a KnowledgePoint if it doesn't exist by full_path.

    Returns:
        True if created, False if skipped (already exists),
        or the existing KnowledgePoint object.
    """
    existing = db.query(KnowledgePoint).filter_by(full_path=full_path).first()
    if existing:
        return existing

    kp = KnowledgePoint(
        name=name,
        parent_id=parent_id,
        depth=depth,
        full_path=full_path,
        description=description,
        importance=importance,
        prerequisite_ids=prerequisite_ids,
    )
    db.add(kp)
    db.flush()  # Make visible to subsequent queries
    return True
