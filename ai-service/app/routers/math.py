import sympy as sp
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from ..schemas import MathRequest, MathResponse

router = APIRouter()


def _run(request: MathRequest) -> MathResponse:
    variable = request.variable or "x"
    x = sp.Symbol(variable)
    expression = request.expression.strip()
    if expression.endswith("=0") and "==" not in expression:
        expression = expression[:-2]

    try:
        expr = sp.sympify(expression)
    except (sp.SympifyError, TypeError, ValueError) as exc:
        return MathResponse(expression=request.expression, result="", ok=False, error=f"Could not parse expression: {exc}")

    steps = [f"Parsed: {sp.sstr(expr)}"]
    try:
        if request.mode == "solve":
            solutions = sp.solve(expr, x)
            result = sp.sstr(solutions)
            if solutions:
                steps.append("Solved for the variable.")
            else:
                steps.append("No closed-form solution found.")
        elif request.mode == "simplify":
            result = sp.sstr(sp.simplify(expr))
            steps.append("Applied simplification rules.")
        elif request.mode == "derivative":
            result = sp.sstr(sp.diff(expr, x))
            steps.append(f"Differentiated with respect to {variable}.")
        elif request.mode == "integral":
            result = sp.sstr(sp.integrate(expr, x))
            steps.append(f"Integrated with respect to {variable} (constant omitted).")
        elif request.mode == "evaluate":
            result = sp.sstr(sp.N(expr))
            steps.append("Evaluated numerically.")
        else:
            return MathResponse(expression=request.expression, result="", ok=False, error=f"Unknown mode: {request.mode}")
    except Exception as exc:
        return MathResponse(expression=request.expression, result="", ok=False, error=str(exc))

    return MathResponse(expression=request.expression, result=result, steps=steps, ok=True)


@router.post("/math", response_model=MathResponse)
async def math_endpoint(request: MathRequest) -> MathResponse:
    return await run_in_threadpool(_run, request)
