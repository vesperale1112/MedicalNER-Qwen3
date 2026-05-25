---
library_name: peft
license: other
base_model: /aistor/sjtu/hpc_stor01/home/wangxiran/models/Qwen3-8B
tags:
- llama-factory
- lora
- generated_from_trainer
model-index:
- name: qwen3-8b-cot-pro858
  results: []
---

<!-- This model card has been generated automatically according to the information the Trainer had access to. You
should probably proofread and complete it, then remove this comment. -->

# qwen3-8b-cot-pro858

This model is a fine-tuned version of [/aistor/sjtu/hpc_stor01/home/wangxiran/models/Qwen3-8B](https://huggingface.co//aistor/sjtu/hpc_stor01/home/wangxiran/models/Qwen3-8B) on the pro_cot_001_858_complete_schema0413 dataset.
It achieves the following results on the evaluation set:
- Loss: 0.0840

## Model description

More information needed

## Intended uses & limitations

More information needed

## Training and evaluation data

More information needed

## Training procedure

### Training hyperparameters

The following hyperparameters were used during training:
- learning_rate: 0.0001
- train_batch_size: 1
- eval_batch_size: 1
- seed: 42
- gradient_accumulation_steps: 8
- total_train_batch_size: 8
- optimizer: Use adamw_torch with betas=(0.9,0.999) and epsilon=1e-08 and optimizer_args=No additional optimizer arguments
- lr_scheduler_type: cosine
- lr_scheduler_warmup_ratio: 0.03
- num_epochs: 3.0

### Training results

| Training Loss | Epoch  | Step | Validation Loss |
|:-------------:|:------:|:----:|:---------------:|
| 2.2291        | 0.2073 | 20   | 1.4551          |
| 0.1005        | 0.4145 | 40   | 0.1920          |
| 0.0758        | 0.6218 | 60   | 0.1325          |
| 0.0624        | 0.8290 | 80   | 0.1038          |
| 0.0456        | 1.0311 | 100  | 0.0959          |
| 0.0526        | 1.2383 | 120  | 0.0915          |
| 0.0239        | 1.4456 | 140  | 0.0887          |
| 0.031         | 1.6528 | 160  | 0.0869          |
| 0.0145        | 1.8601 | 180  | 0.0859          |
| 0.0738        | 2.0622 | 200  | 0.0851          |
| 0.0494        | 2.2694 | 220  | 0.0846          |
| 0.0512        | 2.4767 | 240  | 0.0843          |
| 0.0336        | 2.6839 | 260  | 0.0840          |
| 0.0382        | 2.8912 | 280  | 0.0841          |


### Framework versions

- PEFT 0.15.2
- Transformers 4.52.4
- Pytorch 2.6.0+cpu
- Datasets 3.6.0
- Tokenizers 0.21.1