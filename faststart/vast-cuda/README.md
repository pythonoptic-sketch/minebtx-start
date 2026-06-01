# BTX Start Vast CUDA Faststart Image

This image template is for rented NVIDIA GPU hosts where the customer already
has a public BTX payout address.

Build:

```bash
docker build -t drinknile/btx-start-vast-cuda:pilot faststart/vast-cuda
```

Run:

```bash
docker run --gpus all --rm \
  -e BTX_ADDRESS='btx1z...YOUR_BTX_ADDRESS...' \
  -e BTX_WORKER='vast-4090-de-black' \
  drinknile/btx-start-vast-cuda:pilot
```

Optional rental gate:

```bash
docker run --gpus all --rm \
  -e BTX_ADDRESS='btx1z...YOUR_BTX_ADDRESS...' \
  -e BTX_WORKER='vast-4090-de-black' \
  -e BTX_MEASURED_NPS='76000' \
  -e BTX_NETWORK_NPS='2338067' \
  -e BTX_RENTAL_HOURLY_USD='0.50' \
  -e BTX_MAX_COST_PER_BTX_USD='1.00' \
  drinknile/btx-start-vast-cuda:pilot
```

The image still routes rewards to the user's own address. It does not create or
hold wallet keys.
