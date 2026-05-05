# Attention Is All You Need

**Authors:** Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin
**Year:** 2017
**Venue:** NeurIPS
**arXiv:** https://arxiv.org/abs/1706.03762
**Code:** https://github.com/tensorflow/tensor2tensor

## Abstract

The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the **Transformer**, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves **28.4 BLEU on the WMT 2014 English-to-German translation task**, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of **41.8 after training for 3.5 days on eight GPUs**, a small fraction of the training costs of the best models from the literature.

## Introduction

Recurrent neural networks, long short-term memory and gated recurrent neural networks in particular, have been firmly established as state of the art approaches in sequence modeling and transduction problems such as language modeling and machine translation. Recurrent models typically factor computation along the symbol positions of the input and output sequences, which precludes parallelization within training examples. Attention mechanisms have become an integral part of compelling sequence modeling and transduction models in various tasks. In this work we propose the Transformer, a model architecture eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output.

## Model Architecture

The Transformer follows an encoder-decoder structure using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder.

**Encoder:** stack of N=6 identical layers. Each layer has two sub-layers: (1) a multi-head self-attention mechanism, and (2) a position-wise fully connected feed-forward network. We employ a residual connection around each of the two sub-layers, followed by layer normalization. All sub-layers in the model produce outputs of dimension d_model = 512.

**Decoder:** also a stack of N=6 identical layers. In addition to the two sub-layers in each encoder layer, the decoder inserts a third sub-layer, which performs multi-head attention over the output of the encoder stack.

**Attention:** Scaled Dot-Product Attention. We compute attention as `Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V`.

**Multi-Head Attention:** allows the model to jointly attend to information from different representation subspaces at different positions. We use h=8 parallel attention heads. For each of these we use d_k = d_v = d_model/h = 64.

**Position-wise Feed-Forward Networks:** each layer contains FFN(x) = max(0, xW_1 + b_1) W_2 + b_2. Inner dimension d_ff = 2048.

**Positional Encoding:** since our model contains no recurrence and no convolution, we add positional encodings to the input embeddings. We use sine and cosine functions of different frequencies.

## Training

We trained on the WMT 2014 English-German dataset (4.5M sentence pairs) and WMT 2014 English-French dataset (36M sentence pairs).

- **Hardware:** 8 NVIDIA P100 GPUs.
- **Optimizer:** Adam with β1=0.9, β2=0.98, ε=10^-9.
- **Learning rate schedule:** lrate = d_model^-0.5 * min(step_num^-0.5, step_num * warmup_steps^-1.5) with warmup_steps=4000.
- **Regularization:** Residual Dropout (P_drop = 0.1), Label Smoothing (ε_ls = 0.1).
- **Base model:** trained for 100,000 steps (12 hours).
- **Big model:** trained for 300,000 steps (3.5 days).

## Results

| Model | EN-DE BLEU | EN-FR BLEU | Training Cost (FLOPs) |
|-------|-----------|-----------|----------------------|
| ByteNet | 23.75 | — | — |
| Deep-Att + PosUnk | — | 39.2 | 1.0 × 10^20 |
| GNMT + RL | 24.6 | 39.92 | 2.3 × 10^19 |
| ConvS2S | 25.16 | 40.46 | 9.6 × 10^18 |
| MoE | 26.03 | 40.56 | 2.0 × 10^19 |
| **Transformer (base)** | **27.3** | **38.1** | 3.3 × 10^18 |
| **Transformer (big)** | **28.4** | **41.8** | 2.3 × 10^19 |

Our base model surpasses all previously published models and ensembles, at a fraction of the training cost. The big model achieves 28.4 BLEU on EN-DE, establishing a new state of the art (training for 3.5 days on 8 P100 GPUs).

## Conclusion

In this work, we presented the Transformer, the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention. The model achieves state-of-the-art results while being significantly more parallelizable and faster to train than recurrent and convolutional models. Code available at: https://github.com/tensorflow/tensor2tensor
