# FogHacks
DLM and RL implemented.
Download musiq_ckpt.npz from drive and place it in musiq/.
to run -  python -m rl.train_ppo

For Diffractsim, please pip install matplotlib, numpy, scipy, progressbar

GPU acceleration requires having either CuPy or JAX installed along with CUDA on your computer. To use GPU acceleration with CuPy in your simulations,edit the following line:

```bash
diffractsim.set_backend("CUDA")
```
or
```bash
diffractsim.set_backend("JAX")
```
