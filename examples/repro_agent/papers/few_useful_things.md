# A Few Useful Things to Know about Machine Learning

**Author:** Pedro Domingos
**Year:** 2012
**Venue:** Communications of the ACM
**URL:** https://homes.cs.washington.edu/~pedrod/papers/cacm12.pdf

## Abstract

Machine learning algorithms can figure out how to perform important tasks by generalizing from examples. This is often feasible and cost-effective where manual programming is not. As more data becomes available, more ambitious problems can be tackled. As a result, machine learning is widely used in computer science and other fields. However, developing successful machine learning applications requires a substantial amount of "black art" that is hard to find in textbooks. This article summarizes twelve key lessons that machine learning researchers and practitioners have learned. These include pitfalls to avoid, important issues to focus on, and answers to common questions.

## 1. Learning = Representation + Evaluation + Optimization

All learners are combinations of three components:
- **Representation:** the formal language the classifier is expressed in (instances, hyperplanes, decision trees, sets of rules, neural networks, graphical models)
- **Evaluation:** an evaluation function (objective/scoring) that distinguishes good classifiers from bad ones (accuracy/error rate, precision/recall, squared error, likelihood, posterior probability, information gain, K-L divergence, cost/utility, margin)
- **Optimization:** the method to search among classifiers for the highest-scoring one (greedy search, beam search, branch-and-bound, gradient descent, conjugate gradient, quadratic programming, linear programming)

## 2. It's Generalization that Counts

The fundamental goal of machine learning is to generalize beyond the examples in the training set. Test set error is the only meaningful metric — training set error is misleading. **Don't ever use test data for any decision** (like model selection); reserve it only for the final evaluation.

## 3. Data Alone Is Not Enough

Every learner must embody some knowledge or assumptions beyond the data it's given to generalize. This was formalized in Wolpert's "no free lunch" theorem: averaged over all possible learning problems, no learner is better than any other. Strong assumptions, when correct, make learning possible with much less data.

## 4. Overfitting Has Many Faces

Overfitting comes in many forms. Bias = error from the algorithm's tendency to learn the same wrong things. Variance = error from the algorithm's tendency to learn random things irrespective of signal. Strong false assumptions can be better than weak true ones. Cross-validation can help combat overfitting, but is not a panacea — using it to make many parameter choices reintroduces the problem.

## 5. Intuition Fails in High Dimensions

The curse of dimensionality. As dimensionality increases, the volume of space grows exponentially. Most points become approximately equidistant from each other, breaking distance-based methods. Learners that successfully generalize in high dimensions exploit lower-dimensional structure (manifolds, sparsity).

## 6. Theoretical Guarantees Are Not What They Seem

PAC bounds are usually loose. Asymptotic guarantees say nothing about finite-sample behavior. Theoretical guarantees should be used as a source of intuition, not as a basis for empirical claims.

## 7. Feature Engineering Is the Key

Most of the effort in real ML projects is in feature engineering, not in choosing or tuning the algorithm. Bad features make learning hopeless; good features make almost any algorithm work.

## 8. More Data Beats a Cleverer Algorithm

A dumb algorithm with lots of data beats a clever one with modest amounts. The complexity bottleneck has shifted from data scarcity to data abundance and the human time required to extract knowledge from it.

## 9. Learn Many Models, Not Just One

Model ensembles consistently outperform any single model. Bagging, boosting, and stacking all reliably improve predictions, often substantially. The best entries in most ML competitions are ensembles.

## 10. Simplicity Does Not Imply Accuracy

Occam's razor is widely misapplied in ML. Simpler models do not generalize better in general — only in some cases. The form of the bias–variance tradeoff means that excessively simple models systematically underperform.

## 11. Representable Does Not Imply Learnable

Just because a function can be represented does not mean it can be learned from finite data with a tractable algorithm. The set of efficiently learnable functions is much smaller than the set of representable ones.

## 12. Correlation Does Not Imply Causation

Predictive correlations may not reflect causal structure. Acting on a correlation that doesn't reflect causation can be ineffective or counterproductive. Inferring causation from observational data requires interventions or strong assumptions.

## Conclusion

Like any discipline, machine learning has a lot of "folk wisdom" that can be hard to come by but is crucial for success. This article summarized some of the most salient items. For more, books like Mitchell (1997), Hastie et al. (2009), and Bishop (2006) are good places to start.
