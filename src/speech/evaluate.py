from pprint import pprint

import pandas as pd
import sys
from common import info
from playground.client import send_request
from tuning_STT.calculate import calculate_ser, calculate_cos, load_models
from pathlib import Path
from openai import OpenAI
from common.auth_ import getKey


# 완성된 xlsx파일에서 정답 데이터를 제거
def remove_correct(filePath=None) -> Path:
    if filePath is None:
        filePath = info.open_dialog(False)
    df = pd.read_excel(filePath)
    user_content = df["User content"]
    stt_result = df["STT Result"]

    current_uc = ''
    before_stt = []

    # 기존 DataFrame의 구조를 유지한 채로 새로운 DataFrame 생성
    df2 = pd.DataFrame(columns=df.columns)

    for i in range(len(user_content)):
        if user_content[i][-1] == '.':
            user_content[i] = user_content[i][:-1]

        if user_content[i].replace(" ", "") == current_uc.replace(" ", ""):
            if (user_content[i].replace(" ", "") != stt_result[i].replace(" ", "")
                    and stt_result[i].replace(" ", "") not in before_stt):
                new_row = df.iloc[[i]]  # 현재 행을 그대로 새로운 df2에 추가
                df2 = pd.concat([df2, new_row], ignore_index=True)
                before_stt.append(stt_result[i])
        else:
            current_uc = user_content[i]
            if stt_result[i].replace(" ", "") == current_uc.replace(" ", ""):
                before_stt = []
            else:
                before_stt = [stt_result[i]]
                new_row = df.iloc[[i]]  # 현재 행을 그대로 새로운 df2에 추가
                df2 = pd.concat([df2, new_row], ignore_index=True)

    newFilePath = filePath.with_name(f"{filePath.stem}_onlyError{filePath.suffix}")
    df2.to_excel(newFilePath, index=False)
    print("정답 데이터 제거 완료.")
    return newFilePath


# 완성된 엑셀 파일에서 SER을 계산
def evaluate_SER(filePath=None) -> Path:
    if filePath is None:
        filePath = info.open_dialog(False)
    df = pd.read_excel(filePath)
    df2 = pd.DataFrame(columns=["User content", "STT Result"])

    df2["User content"] = df["User content"].str.replace(" ", "")
    df2["STT Result"] = df["STT Result"].str.replace(" ", "")

    # SER 계산
    try:
        df['SER'] = [calculate_ser(orig, stt)
                     for orig, stt in zip(df2["User content"], df2["STT Result"])]
    except:
        print("오류 발생!")
        sys.exit()

    newFilePath = filePath.with_name(f"{filePath.stem}_SER{filePath.suffix}")
    df.to_excel(newFilePath, index=False)
    print("SER 계산완료.")
    return newFilePath

# 데이터 교정가능여부 확인
def able_to_correct():
    PROMPT = "제시된 문장은 STT과정에서 오류가 발생한 문장이다. 기존 문장으로 수정하라.\
                답변은 수정한 문장만을 출력하고, 문장 부호는 생략한다."
    KEY = getKey('STT')
    client = OpenAI(api_key=KEY)
    filePath = info.open_dialog(False)
    df = pd.read_excel(filePath)

    corrected = []
    corrected_ser = []
    for index, row in df.iterrows():
        orig = row["User content"]
        stt = row["STT Result"]
        conversation_history = [
            {
                "role": "system",
                "content": PROMPT
            }
        ]
        response = send_request(client, conversation_history, stt)
        print(f"{index+1}: {orig}\t{response}")
        ser = calculate_ser(orig, response)
        corrected.append(response)
        corrected_ser.append(ser)

    df["Corrected"] = corrected
    df["Corrected_SER"] = corrected_ser

    newFilePath = filePath.with_stem(filePath.stem + "_corrected")
    df.to_excel(newFilePath, index=False)

def evaluate_score():
    filePath = info.open_dialog(False)
    df = pd.read_excel(filePath)
    tokenizer_bert, model_bert = load_models()
    print("모델 로드 완료")

    cos1 = []
    cos2 = []
    ser1 = []
    ser2 = []
    # SER, COS 계산
    for index, row in df.iterrows():
        orig = row["User content"]
        stt = row["STT Result"]
        cor = row["Corrected"]
        ser1.append(calculate_ser(orig, stt))
        ser2.append(calculate_ser(orig, cor))
        cos1.append(calculate_cos(tokenizer_bert, model_bert, orig, stt))
        cos2.append(calculate_cos(tokenizer_bert, model_bert, orig, cor))
        print(f"{index+1} - SER: {ser1[-1]} -> {ser2[-1]}, COS: {cos1[-1]} -> {cos2[-1]}")

    data = {
        "User content": df["User content"],
        "STT Result": df["STT Result"],
        "Corrected": df["Corrected"],
        "SER(User-STT)": ser1,
        "COS(User-STT)": cos1,
        "SER(User-COR)": ser2,
        "COS(User-COR)": cos2
    }
    df2 = pd.DataFrame(data)
    df2.to_excel(filePath.with_stem(filePath.stem + "_evaluated"), index=False)

# 평가모델
def evaluation_model():
    pass


if __name__ == '__main__':
    fp = info.open_dialog(False)
    df = pd.read_excel(fp)
    plot_relative_change_with_smoothing(df["SER(User-STT)"], df["SER(User-COR)"], "SER")
    plot_relative_change_with_smoothing(df["COS(User-STT)"], df["COS(User-COR)"], "COS")

    # evaluate_score()
    # able_to_correct()
