import { experimental_evaluate as evaluate } from 'ai';

function fail(message) {
  process.stderr.write(message + '\n');
  process.exit(2);
}

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf8');
}

function toQuestion(question) {
  if (question.type === 'choice') {
    if (!Array.isArray(question.choices) || question.choices.length === 0) {
      throw new Error(`${question.question_id}: choice requires choices`);
    }
    return {
      type: 'choice',
      instructions: question.instructions,
      criteria: Object.fromEntries(
        question.choices.map((choice) => [choice, choice]),
      ),
    };
  }

  if (question.type === 'score') {
    if (!Array.isArray(question.score_levels) || question.score_levels.length < 2) {
      throw new Error(`${question.question_id}: score requires score_levels`);
    }
    return {
      type: 'score',
      instructions: question.instructions,
      criteria: question.score_levels,
    };
  }

  if (question.type === 'boolean') {
    return {
      type: 'boolean',
      instructions: question.instructions,
    };
  }

  throw new Error(`${question.question_id}: unsupported question type ${question.type}`);
}

function normalizeAnswer(questionId, answer, confidenceMap) {
  const confidence =
    typeof confidenceMap?.[questionId] === 'number'
      ? confidenceMap[questionId]
      : null;

  if (answer.type === 'choice') {
    return {
      question_id: questionId,
      type: 'choice',
      value: answer.choice,
      probabilities: answer.probabilities ?? null,
      probability_true: null,
      confidence,
    };
  }

  if (answer.type === 'score') {
    return {
      question_id: questionId,
      type: 'score',
      value: answer.score,
      probabilities: answer.probabilities ?? null,
      probability_true: null,
      confidence,
    };
  }

  if (answer.type === 'boolean') {
    return {
      question_id: questionId,
      type: 'boolean',
      value: answer.probability >= 0.5,
      probabilities: null,
      probability_true: answer.probability,
      confidence: null,
    };
  }

  throw new Error(`${questionId}: unsupported answer type ${answer.type}`);
}

async function main() {
  if (!process.env.AI_GATEWAY_API_KEY && !process.env.VERCEL_OIDC_TOKEN) {
    fail('AI_GATEWAY_API_KEY or VERCEL_OIDC_TOKEN must be set');
  }

  const input = JSON.parse(await readStdin());
  if (input?.schema_version !== 1) {
    fail('unsupported sidecar request schema_version');
  }

  const questionEntries = input.case.questions.map((question) => [
    question.question_id,
    toQuestion(question),
  ]);
  const questions = Object.fromEntries(questionEntries);

  const result = await evaluate({
    model: 'typesafe-ai/jev',
    state: input.case.state,
    questions,
    providerOptions: {
      gateway: {
        zeroDataRetention: true,
      },
    },
  });

  const confidenceMap = result.providerMetadata?.typesafe?.confidence ?? {};
  const answers = Object.entries(result.answers).map(([questionId, answer]) =>
    normalizeAnswer(questionId, answer, confidenceMap),
  );

  const responseModelId =
    result.response?.modelId ??
    result.providerMetadata?.gateway?.modelId ??
    null;

  const output = {
    answers,
    provider_metadata: {
      gateway: result.providerMetadata?.gateway ?? {},
      typesafe: result.providerMetadata?.typesafe ?? {},
      response_model_id: responseModelId,
      rounding: result.rounding ?? null,
    },
    runtime_metadata: {
      adapter: 'ai-sdk-experimental-evaluate',
      requested_model_id: 'typesafe-ai/jev',
      zero_data_retention_requested: true,
    },
    usage: result.usage ?? {},
    cost: {},
    raw_output: {
      answers: result.answers,
      providerMetadata: result.providerMetadata ?? {},
      usage: result.usage ?? {},
      rounding: result.rounding ?? null,
      responseModelId,
    },
  };

  process.stdout.write(JSON.stringify(output));
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : 'unknown Jev sidecar error';
  fail(message);
});
