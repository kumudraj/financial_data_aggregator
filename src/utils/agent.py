import asyncio

from agents import Agent, InputGuardrail, GuardrailFunctionOutput, Runner
from dotenv import load_dotenv
from pydantic import BaseModel

from src.utils.common_utils import fetch_financial_data, convert_numpy_types, default_symbols, default_instructions
from src.utils.logger import structlog

load_dotenv()
log = structlog.get_logger()


class FinancialDataGuardrailOutput(BaseModel):
    is_valid: bool
    reason: str


class FinancialAgent:
    def __init__(self, symbols=None, guardrail_required=True):
        self.symbols = symbols or default_symbols
        self.guardrail_required = guardrail_required

        # Configure agent with or without guardrails
        agent_config = {
            "name": "Summary Agent",
            "instructions": default_instructions,
            "model": "o4-mini",  # or "gpt-3.5-turbo"
        }

        if self.guardrail_required:
            agent_config["input_guardrails"] = [
                InputGuardrail(guardrail_function=self.financial_data_guardrail),
            ]

        self.summary_agent = Agent(**agent_config)

    async def financial_data_guardrail(self, ctx, agent, input_data):
        try:
            # Extract the data part from the input string if it's a string
            if isinstance(input_data, str) and "following financial data:" in input_data:
                import ast
                # Extract the data part after "following financial data:"
                data_str = input_data.split("following financial data:")[-1].strip()
                # Safely evaluate the string representation of the list
                try:
                    input_data = ast.literal_eval(data_str)
                except:
                    input_data = []

            is_valid = bool(input_data and isinstance(input_data, list) and all(
                isinstance(d, dict) and 'symbol' in d for d in input_data))
            reason = "Valid financial data." if is_valid else "Invalid or empty financial data."
            output = FinancialDataGuardrailOutput(is_valid=is_valid, reason=reason)
            log.info(f"Guardrail check is_valid: {is_valid}, reason:{reason}, data:{input_data}")
            return GuardrailFunctionOutput(
                output_info=output,
                tripwire_triggered=not is_valid,
            )
        except Exception as e:
            log.error("Exception in financial_data_guardrail", exc_info=True)
            output = FinancialDataGuardrailOutput(is_valid=False, reason=f"Exception occurred in guardrail: {str(e)}")
            return GuardrailFunctionOutput(
                output_info=output,
                tripwire_triggered=True,
            )

    async def generate_summary(self, data):
        try:
            if not data:
                log.error("No valid financial data to summarize.", exc_info=True)
                return "No valid financial data to summarize."
            # Convert numpy types to native Python types
            data = convert_numpy_types(data)
            prompt = f"Generate a summary for the following financial data: {data}"

            if not self.guardrail_required:
                log.info("Skipping guardrail checks disabled True")

            result = await Runner.run(self.summary_agent, prompt)
            log.info(f"Summary generated summary: {result.final_output}")
            return result.final_output
        except Exception as e:
            log.error("Exception in generate_summary", exc_info=True)
            return "Summary generation failed due to an error."

    async def run(self):
        try:
            log.info("Agent started")
            tasks = [fetch_financial_data(symbol) for symbol in self.symbols]
            results = await asyncio.gather(*tasks)
            # Filter out empty dicts
            results = [r for r in results if r and isinstance(r, dict) and r.get("symbol")]
            if not results:
                log.error("No valid financial data fetched for any symbol.", exc_info=True)
                return
            summary = await self.generate_summary(results)
            log.info(f"Final summary summary: {summary}")
        except Exception as err:
            log.error(f"An error occurred in agent run: {str(err)}", exc_info=True)


async def main():
    agent = FinancialAgent(symbols="TSLA")  # , guardrail_required=False)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
