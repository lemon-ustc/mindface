# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

echo "=============================================================================================================="
echo "Please run the script as: "
echo "bash run.sh EVAL_PATH CKPT_PATH"
echo "For example: bash run.sh path/evalset path/ckpt"
echo "It is better to use the absolute path."
echo "=============================================================================================================="

EVAL_PATH=$1
CKPT_PATH=$2
MODEL_NAME=$3
CUDA_VISIBLE_DEVICES=0

python val.py \
--ckpt_url "$CKPT_PATH" \
--device_id 0 \
--eval_url "$EVAL_PATH" \
--device_target "GPU" \
--model "$MODEL_NAME" \
--target lfw,cfp_fp,agedb_30,calfw,cplfw
