window.DEMO = {
  "title": "鍵付きリズム擬名化 — 聴き比べ",
  "subtitle": "音色を保ったままリズム（音素の継続長）だけを鍵依存に置換する。従来の音色変換（Fang）と対比すると、変化する軸が直交していることが分かる。",
  "updated": "2026-06",
  "model": "R1 / e10_s83230 (CSJ)",
  "config": {
    "DONOR_MODE": "farthest",
    "N_DONORS": 3,
    "A3_CADENCE_WEIGHT": 2.0,
    "KEY_SYS": "paperA-sys-v1"
  },
  "conditions": [
    {
      "id": "A1",
      "label": "無変換",
      "sub": "コピー合成（基準）",
      "timbre": "keep",
      "rhythm": "keep",
      "role": "base"
    },
    {
      "id": "A3",
      "label": "提案：リズム擬名化",
      "sub": "ドナー3名・farthest",
      "timbre": "keep",
      "rhythm": "change",
      "role": "proposed"
    },
    {
      "id": "A3_d1",
      "label": "提案：ドナー1名",
      "sub": "擬似話者性が明確",
      "timbre": "keep",
      "rhythm": "change",
      "role": "proposed",
      "optional": true
    },
    {
      "id": "B_fang",
      "label": "従来 Fang：音色変換",
      "sub": "リズムは素通し",
      "timbre": "change",
      "rhythm": "keep",
      "role": "contrast"
    },
    {
      "id": "C_both",
      "label": "フル匿名化：音色＋リズム",
      "sub": "Fang音色変換＋提案リズム置換",
      "timbre": "change",
      "rhythm": "change",
      "role": "contrast",
      "optional": true
    }
  ],
  "groups": [
    {
      "id": "high",
      "name": "自然性が高い例",
      "note": "UTMOS 上位。提案でも自然さがよく保たれる。"
    },
    {
      "id": "avg",
      "name": "平均的な例",
      "note": "UTMOS が中央付近。典型的な品質。"
    }
  ],
  "samples": [
    {
      "group": "high",
      "spk": "189",
      "uid": "7c905aa10a",
      "text": "植林では",
      "clips": {
        "A1": {
          "wav": "audio/A1/189__7c905aa10a.wav",
          "utmos": 3.63
        },
        "A3": {
          "wav": "audio/A3/189__7c905aa10a.wav",
          "utmos": 4.12,
          "donors": [
            "551",
            "1089",
            "685"
          ]
        },
        "B_fang": {
          "wav": "audio/B_fang/189__7c905aa10a.wav",
          "utmos": 4.29
        },
        "A3_d1": {
          "wav": "audio/A3_d1/189__7c905aa10a.wav",
          "utmos": null,
          "donor": "551",
          "optional": true
        },
        "C_both": {
          "wav": "audio/C_both/189__7c905aa10a.wav",
          "utmos": null,
          "optional": true
        }
      }
    },
    {
      "group": "high",
      "spk": "438",
      "uid": "d4c71de2d7",
      "text": "入っていただいて十五人ばかりの",
      "clips": {
        "A1": {
          "wav": "audio/A1/438__d4c71de2d7.wav",
          "utmos": 3.47
        },
        "A3": {
          "wav": "audio/A3/438__d4c71de2d7.wav",
          "utmos": 4.05,
          "donors": [
            "591",
            "277",
            "571"
          ]
        },
        "B_fang": {
          "wav": "audio/B_fang/438__d4c71de2d7.wav",
          "utmos": 3.58
        },
        "A3_d1": {
          "wav": "audio/A3_d1/438__d4c71de2d7.wav",
          "utmos": null,
          "donor": "591",
          "optional": true
        },
        "C_both": {
          "wav": "audio/C_both/438__d4c71de2d7.wav",
          "utmos": null,
          "optional": true
        }
      }
    },
    {
      "group": "high",
      "spk": "380",
      "uid": "69dbc8a737",
      "text": "何を食べたか",
      "clips": {
        "A1": {
          "wav": "audio/A1/380__69dbc8a737.wav",
          "utmos": 3.44
        },
        "A3": {
          "wav": "audio/A3/380__69dbc8a737.wav",
          "utmos": 3.99,
          "donors": [
            "159",
            "566",
            "584"
          ]
        },
        "B_fang": {
          "wav": "audio/B_fang/380__69dbc8a737.wav",
          "utmos": 3.27
        },
        "A3_d1": {
          "wav": "audio/A3_d1/380__69dbc8a737.wav",
          "utmos": null,
          "donor": "159",
          "optional": true
        },
        "C_both": {
          "wav": "audio/C_both/380__69dbc8a737.wav",
          "utmos": null,
          "optional": true
        }
      }
    },
    {
      "group": "avg",
      "spk": "235",
      "uid": "b88bd0f0f4",
      "text": "昨日なんかはえー雪とか降ってえらい寒いことになってるんですけれどもえー",
      "clips": {
        "A1": {
          "wav": "audio/A1/235__b88bd0f0f4.wav",
          "utmos": 2.92
        },
        "A3": {
          "wav": "audio/A3/235__b88bd0f0f4.wav",
          "utmos": 2.79,
          "donors": [
            "256",
            "198",
            "243"
          ]
        },
        "B_fang": {
          "wav": "audio/B_fang/235__b88bd0f0f4.wav",
          "utmos": 3.3
        },
        "A3_d1": {
          "wav": "audio/A3_d1/235__b88bd0f0f4.wav",
          "utmos": null,
          "donor": "256",
          "optional": true
        },
        "C_both": {
          "wav": "audio/C_both/235__b88bd0f0f4.wav",
          "utmos": null,
          "optional": true
        }
      }
    },
    {
      "group": "avg",
      "spk": "544",
      "uid": "566d2bc245",
      "text": "えさてえここでまー私の仕事の中でのキーマンと言える方をちょっとお話ししたいんですけれどもえ実はワイさんという方が女性がいらっしゃいます",
      "clips": {
        "A1": {
          "wav": "audio/A1/544__566d2bc245.wav",
          "utmos": 3.02
        },
        "A3": {
          "wav": "audio/A3/544__566d2bc245.wav",
          "utmos": 2.79,
          "donors": [
            "885",
            "199",
            "978"
          ]
        },
        "B_fang": {
          "wav": "audio/B_fang/544__566d2bc245.wav",
          "utmos": 2.72
        },
        "A3_d1": {
          "wav": "audio/A3_d1/544__566d2bc245.wav",
          "utmos": null,
          "donor": "885",
          "optional": true
        },
        "C_both": {
          "wav": "audio/C_both/544__566d2bc245.wav",
          "utmos": null,
          "optional": true
        }
      }
    },
    {
      "group": "avg",
      "spk": "598",
      "uid": "6f05d75482",
      "text": "私は小学校三年生の三学期で転校して都内のある区立の小学校に入りました",
      "clips": {
        "A1": {
          "wav": "audio/A1/598__6f05d75482.wav",
          "utmos": 3.05
        },
        "A3": {
          "wav": "audio/A3/598__6f05d75482.wav",
          "utmos": 2.79,
          "donors": [
            "551",
            "1089",
            "685"
          ]
        },
        "B_fang": {
          "wav": "audio/B_fang/598__6f05d75482.wav",
          "utmos": 2.98
        },
        "A3_d1": {
          "wav": "audio/A3_d1/598__6f05d75482.wav",
          "utmos": null,
          "donor": "551",
          "optional": true
        },
        "C_both": {
          "wav": "audio/C_both/598__6f05d75482.wav",
          "utmos": null,
          "optional": true
        }
      }
    }
  ]
};
