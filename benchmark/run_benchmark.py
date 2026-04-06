import json
import sys
import math
from pathlib import Path
from datetime import datetime

# Añadir backend al path
sys.path.append(str(Path(__file__).parent.parent / "backend"))
from app.matcher import compare_cv_to_job
from app.cv_parser import extract_text_from_pdf

def dcg_at_k(relevances, k=3):
    relevances = relevances[:k]
    if not relevances:
        return 0.0
    return sum(rel / math.log2(idx + 2) for idx, rel in enumerate(relevances))

def ndcg_at_k(ranking_obtenido, relevancias_esperadas, k=3):
    # relevancias_esperadas map cv_file_name -> relevance (0-3)
    relevances = [relevancias_esperadas.get(cv, 0) for cv, _ in ranking_obtenido]
    ideal_relevances = sorted(list(relevancias_esperadas.values()), reverse=True)
    
    dcg = dcg_at_k(relevances, k)
    idcg = dcg_at_k(ideal_relevances, k)
    
    if idcg == 0:
        return 0.0
    return dcg / idcg

def precision_at_k(ranking_obtenido, relevancias_esperadas, k=3, threshold=2):
    top_k = ranking_obtenido[:k]
    if not top_k:
        return 0.0
    relevant_count = sum(1 for cv, _ in top_k if relevancias_esperadas.get(cv, 0) >= threshold)
    return relevant_count / len(top_k)

def mrr(ranking_obtenido, relevancias_esperadas, max_relevance=3):
    for idx, (cv, _) in enumerate(ranking_obtenido):
        if relevancias_esperadas.get(cv, 0) == max_relevance:
            return 1.0 / (idx + 1)
    return 0.0

def run_benchmark(config_path, balance=0.5, strictness="normal"):
    base_dir = Path(__file__).parent
    config_file = base_dir / config_path
    
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    resultados = {}
    
    for category, cat_data in config.items():
        print(f"\nProcesando categoría: {category} ({cat_data['descripcion']})")
        oferta_path = base_dir / cat_data["oferta"]
        cvs_dir = base_dir / "dataset" / category / "cvs"
        
        if not oferta_path.exists():
            print(f"No se encuentra la oferta {oferta_path}, saltando")
            continue
            
        with open(oferta_path, "r", encoding="utf-8") as f:
            job_description = f.read()
            
        if not cvs_dir.exists() or not any(cvs_dir.iterdir()):
            print(f"No hay CVs en {cvs_dir.relative_to(base_dir)}, saltando")
            continue
            
        # Parse expected rankings
        expected_dict = {item["cv"]: item["relevancia"] for item in cat_data["ranking_esperado"]}
        
        # Evaluar CVs localmente
        scores = []
        cv_files = list(cvs_dir.glob("*.pdf"))
        
        if not cv_files:
            print(f"No hay PDFs listos en {cvs_dir.relative_to(base_dir)}")
            continue
            
        for cv_path in cv_files:
            try:
                cv_text = extract_text_from_pdf(cv_path)
                score = compare_cv_to_job(cv_text, job_description, strictness, balance)
                scores.append((cv_path.name, score))
            except Exception as e:
                print(f"Error procesando {cv_path.name}: {e}")
                scores.append((cv_path.name, 0.0))
        
        # Sort by score desc
        scores.sort(key=lambda x: x[1], reverse=True)
        
        print(f"Ranking obtenido (Top {min(3, len(scores))}):")
        for i, (cv, sc) in enumerate(scores[:3]):
            rel = expected_dict.get(cv, 0)
            print(f"  {i+1}. {cv} - Score: {sc:.3f} - Rel. real: {rel}")
            
        cat_ndcg = ndcg_at_k(scores, expected_dict, k=3)
        cat_prec = precision_at_k(scores, expected_dict, k=3)
        cat_mrr = mrr(scores, expected_dict)
        
        resultados[category] = {
            "ndcg@3": cat_ndcg,
            "precision@3": cat_prec,
            "mrr": cat_mrr,
            "ranking": [{"cv": cv, "score": sc, "relevancia_real": expected_dict.get(cv, 0)} for cv, sc in scores]
        }
        
    if not resultados:
        print("\nNo se pudo calcular métricas completas para ninguna categoría. (Asegúrate de haber añadido PDFs)")
        return
        
    print("\n--- RESUMEN DE MÉTRICAS ---")
    print(f"{'Categoría':<15} | {'NDCG@3':<8} | {'Prec@3':<8} | {'MRR':<8}")
    print("-" * 50)
    
    avg_ndcg = sum(r["ndcg@3"] for r in resultados.values()) / len(resultados)
    avg_prec = sum(r["precision@3"] for r in resultados.values()) / len(resultados)
    avg_mrr = sum(r["mrr"] for r in resultados.values()) / len(resultados)
    
    for cat, r in resultados.items():
        print(f"{cat:<15} | {r['ndcg@3']:.3f}   | {r['precision@3']:.3f}   | {r['mrr']:.3f}")
        
    print("-" * 50)
    print(f"{'PROMEDIO':<15} | {avg_ndcg:.3f}   | {avg_prec:.3f}   | {avg_mrr:.3f}")
    
    results_dir = base_dir / "results"
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = results_dir / f"benchmark_{timestamp}.json"
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "config": {"balance": balance, "strictness": strictness},
            "metrics": {
                "avg_ndcg@3": avg_ndcg,
                "avg_precision@3": avg_prec,
                "avg_mrr": avg_mrr
            },
            "categories": resultados
        }, f, indent=2, ensure_ascii=False)
        
    print(f"\nResultados detallados guardados en {out_file.relative_to(base_dir)}")

if __name__ == "__main__":
    run_benchmark("expected_rankings.json")
