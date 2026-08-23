// Isolation Forest, implemented directly so Artifact 1 can animate real cuts
// rather than replay a canned animation.
//
// The idea in one sentence: slice the plane with random axis-aligned cuts and count
// how many it takes to strand a point alone. Outliers strand fast.

// Expected path length of an unsuccessful BST search over n points — the
// normalisation that turns a raw depth into a comparable score.
function cNorm(n) {
  if (n <= 1) return 0;
  return 2 * (Math.log(n - 1) + 0.5772156649) - (2 * (n - 1)) / n;
}

function buildTree(points, depth, maxDepth, rng) {
  if (depth >= maxDepth || points.length <= 1) {
    return { leaf: true, size: points.length, depth };
  }
  const dim = Math.floor(rng.next() * points[0].length);
  let lo = Infinity, hi = -Infinity;
  for (const p of points) { lo = Math.min(lo, p[dim]); hi = Math.max(hi, p[dim]); }
  if (lo === hi) return { leaf: true, size: points.length, depth };

  const split = rng.uniform(lo, hi);
  const left = [], right = [];
  for (const p of points) (p[dim] < split ? left : right).push(p);
  return {
    leaf: false, dim, split,
    left: buildTree(left, depth + 1, maxDepth, rng),
    right: buildTree(right, depth + 1, maxDepth, rng),
  };
}

function pathLengthFor(point, node, depth = 0) {
  if (node.leaf) return depth + cNorm(node.size);
  return point[node.dim] < node.split
    ? pathLengthFor(point, node.left, depth + 1)
    : pathLengthFor(point, node.right, depth + 1);
}

class IsolationForest {
  constructor({ trees = 100, sampleSize = 256, seed = 1337 } = {}) {
    Object.assign(this, { trees, sampleSize, seed, forest: [] });
  }

  fit(data) {
    const { Rng } = (typeof require !== 'undefined')
      ? require('./prng.js') : window.Demo;
    const rng = new Rng(this.seed);
    const n = Math.min(this.sampleSize, data.length);
    const maxDepth = Math.ceil(Math.log2(Math.max(2, n)));
    this.norm = cNorm(n);
    this.forest = [];
    for (let t = 0; t < this.trees; t++) {
      const sample = [];
      for (let i = 0; i < n; i++) sample.push(data[Math.floor(rng.next() * data.length)]);
      this.forest.push(buildTree(sample, 0, maxDepth, rng));
    }
    return this;
  }

  avgPathLength(point) {
    let total = 0;
    for (const tree of this.forest) total += pathLengthFor(point, tree);
    return total / this.forest.length;
  }

  // Higher score = more anomalous. Range (0, 1).
  score(point) {
    return Math.pow(2, -this.avgPathLength(point) / this.norm);
  }

  // Threshold at the given quantile of the training data's own scores.
  percentileThreshold(data, q = 0.99) {
    const scores = data.map((p) => this.score(p)).sort((a, b) => a - b);
    return scores[Math.min(scores.length - 1, Math.floor(q * scores.length))];
  }

  // Decision surface for rendering the fence in Artifacts 1 and 2.
  grid(xRange, yRange, steps = 60) {
    const out = [];
    for (let i = 0; i < steps; i++) {
      const row = [];
      const x = xRange[0] + ((xRange[1] - xRange[0]) * i) / (steps - 1);
      for (let j = 0; j < steps; j++) {
        const y = yRange[0] + ((yRange[1] - yRange[0]) * j) / (steps - 1);
        row.push(this.score([x, y]));
      }
      out.push(row);
    }
    return out;
  }
}

const api = { IsolationForest, pathLengthFor, cNorm, buildTree };
if (typeof module !== 'undefined' && module.exports) module.exports = api;
if (typeof window !== 'undefined') window.Demo = Object.assign(window.Demo || {}, api);
