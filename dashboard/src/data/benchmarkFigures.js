export const hdfs = {
  dataset: "LogHub HDFS_v1",
  blocksTotal: 50000,
  blocksAnomalous: 1464,
  anomalyRate: "2.93%",
  testNormal: 9708,
  testAnomaly: 1464,
  rocAuc: 0.793,
  averagePrecision: 0.5974,
  operatingPoint: "validation-p99",
  lstm: {
    label: "Drain3 + LSTM autoencoder",
    precision: 0.839,
    recall: 0.374,
    f1: 0.517,
    falsePositiveRate: 0.0108,
    falseAlarms: 105,
  },
  keyword: {
    label: "ERROR/WARN keyword baseline",
    precision: 0.304,
    recall: 0.656,
    f1: 0.416,
    falsePositiveRate: 0.2266,
    falseAlarms: 2200,
  },
  falseAlarmReduction: "21x",
  matchedRecallPrecision: 0.35,
};

export const llmLatency = {
  cpuSeconds: 47.07,
  gpuSeconds: 4.21,
  speedup: "11.2x",
  gpu: "RTX 3050 6 GB",
};

export const pipelineIntegrity = {
  delivery: "100%",
  assembly: "100%",
  splitClosures: 0,
};
