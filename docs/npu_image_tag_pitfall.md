# NPU 镜像 tag 缓存坑（必读）

## TL;DR

**不要重新 push 已经在用的同名 tag**。compute 节点不会主动 re-pull，本地缓存什么就用什么，registry 上覆盖了它也不知道。

每次重 build 必须用新 tag（`v1.0` → `v1.1` → `v1.2` 或带日期 `v1.0-20260525`）。

---

## 我们踩的坑（2026-05-25）

跑 `vc submit ... -i sjtu_wumengyue-xiranwang-medicalner-qwen3:v1.0` 做 predict，
报：

```
File "/opt/LLaMA-Factory/src/llamafactory/model/loader.py", line 28, in <module>
    from trl import AutoModelForCausalLMWithValueHead
ImportError: cannot import name 'AutoModelForCausalLMWithValueHead' from 'trl'
```

奇怪之处：
- 调试机上 `docker pull v1.0` 后进镜像看，**根本没有 `/opt/LLaMA-Factory`**
- 但 compute 节点报错栈里实实在在出现了这个路径
- digest 看着一致（debug 机的本地缓存 vs registry）

## 真相

两份不同的镜像，被同一个 tag 引用：

| | 我们 push 到 registry 的当前 v1.0 | compute 节点本地缓存的"v1.0" |
|---|---|---|
| `/opt/LLaMA-Factory` | 不存在 | 存在（May 18 17:12 烤进去的） |
| `__editable__.llamafactory-0.9.3.pth` | 不存在 | 存在，指向 `/opt/LLaMA-Factory/src` |
| llamafactory 装法 | pip 装 site-packages | editable，源码在 /opt |
| trl 兼容性 | 兼容 0.9.3 loader.py | 跟 editable 那份 loader.py 对不上 |

那份带 `/opt/LLaMA-Factory` 的镜像应该是 5/18 build 的早期版本（基础镜像里可能默认带，或当时 pip 走了 editable 路径）。之后我们**用相同 tag `v1.0` 多次重 build & push**——registry 被更新了，但 compute 节点本地缓存依然是 5/18 那份。

`docker pull` 只刷调试机自己的本地缓存，**不会通知 compute 节点**。

## 现象的解释

- 5/19 那次跑通：可能正好派到了某个还没缓存 v1.0 的节点，全网新拉了对的版本；或者那份老镜像里 trl 还能勉强 import
- 5/25 这次失败：派到了带 5/18 缓存的节点，老的 editable install + 不兼容的 trl 直接炸
- 同一份 `docker_run --rm` 拉一份新的镜像看着没问题：因为你拉的就是 registry 当前版本，跟 compute 节点缓存无关

## 怎么避免

**永远不要重新 push 同一个 tag**。每次重大构建用新 tag：

```bash
# 推荐：递增版本号
IMAGE_TAG=v1.0 bash scripts/build_medicalner_qwen3_npu_image.sh --push
# 改了 Dockerfile/requirements 后：
IMAGE_TAG=v1.1 bash scripts/build_medicalner_qwen3_npu_image.sh --push

# 或带日期 / commit hash
IMAGE_TAG=v1.0-20260525 bash scripts/build_medicalner_qwen3_npu_image.sh --push
IMAGE_TAG=v1.0-b2a80ef bash scripts/build_medicalner_qwen3_npu_image.sh --push
```

`vc submit` 时 `-i` 跟着改。

## 这次的修复

build & push `v1.0-fix`，submit 用：
```
-i hub.szaic.com/sjtu/sjtu_wumengyue-xiranwang-medicalner-qwen3:v1.0-fix
```
compute 节点没缓存这个新 tag，被迫全网新拉，拿到对的版本，predict 直接走通。

`v1.0` 这个 tag 短期内别再用——不知道哪些节点还缓存着哪份老的。
