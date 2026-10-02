from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient()

state = "Me cobraron dos veces. Ayuda urgente por favor."

questions = {
      "billing": Noul(instructions="¿Es sobre facturación?"),
      "tone": Choice(
          instructions="¿Cuál es el tono?",
          criteria={"calmado": None, "molesto": None}
      ),
      "urgency": Score(
          instructions="¿Qué tan urgente es?",
          criteria=["bajo", "medio", "alto"]
      ),
  }

result = client.system_one(state, questions)

print("billing:", result.nouls["billing"].noul)
print("tone:", result.choices["tone"].choice)
print("urgency:", result.scores["urgency"].score)
