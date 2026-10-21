import os
import sqlite3

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, avg, desc


def create_spark_session():
    """
    Create local PySpark session for BDA analytics.
    """
    return (
        SparkSession.builder
        .appName("DarkPatternBDAAnalytics")
        .master("local[*]")
        .getOrCreate()
    )


def load_data(spark, db_path):
    """
    Load SQLite database tables into PySpark DataFrames.
    """

    connection = sqlite3.connect(db_path)

    analysis_query = """
        SELECT *
        FROM analysis_results
    """

    pattern_query = """
        SELECT *
        FROM detected_patterns
    """

    import pandas as pd

    analysis_pd = pd.read_sql_query(
        analysis_query,
        connection
    )

    pattern_pd = pd.read_sql_query(
        pattern_query,
        connection
    )

    connection.close()

    analysis_df = spark.createDataFrame(analysis_pd)
    pattern_df = spark.createDataFrame(pattern_pd)

    return analysis_df, pattern_df


def run_bda_analysis(db_path):
    """
    Run Big Data analytics using PySpark.
    """

    spark = create_spark_session()

    try:

        analysis_df, pattern_df = load_data(
            spark,
            db_path
        )

        # 1. Pattern frequency
        pattern_frequency = (
            pattern_df
            .groupBy("pattern_type")
            .agg(
                count("*").alias("total_detected")
            )
            .orderBy(
                desc("total_detected")
            )
        )

        # 2. Severity distribution
        severity_distribution = (
            pattern_df
            .groupBy("severity")
            .agg(
                count("*").alias("total_detected")
            )
            .orderBy(
                desc("total_detected")
            )
        )

        # 3. Industry-wise analysis
        industry_analysis = (
            analysis_df
            .groupBy("industry_category")
            .agg(
                count("*").alias("total_websites"),
                avg(
                    "credibility_score"
                ).alias(
                    "average_credibility_score"
                )
            )
            .orderBy(
                desc("total_websites")
            )
        )

        # 4. Domain analysis
        domain_analysis = (
            analysis_df
            .groupBy("domain")
            .agg(
                count("*").alias("analysis_count"),
                avg(
                    "credibility_score"
                ).alias(
                    "average_credibility_score"
                )
            )
            .orderBy(
                desc("analysis_count")
            )
        )

        # Display results in terminal
        print("\n========== BDA: PATTERN FREQUENCY ==========")
        pattern_frequency.show(truncate=False)

        print("\n========== BDA: SEVERITY DISTRIBUTION ==========")
        severity_distribution.show(truncate=False)

        print("\n========== BDA: INDUSTRY ANALYSIS ==========")
        industry_analysis.show(truncate=False)

        print("\n========== BDA: DOMAIN ANALYSIS ==========")
        domain_analysis.show(truncate=False)

        return {
            "pattern_frequency": pattern_frequency,
            "severity_distribution": severity_distribution,
            "industry_analysis": industry_analysis,
            "domain_analysis": domain_analysis
        }

    finally:
        spark.stop()

def get_bda_summary(db_path):
    """
    Run PySpark analytics and return JSON-serializable results.
    """

    spark = create_spark_session()

    try:
        analysis_df, pattern_df = load_data(
            spark,
            db_path
        )

        # Pattern frequency
        pattern_frequency_df = (
            pattern_df
            .groupBy("pattern_type")
            .agg(
                count("*").alias("total_detected")
            )
            .orderBy(desc("total_detected"))
        )

        # Severity distribution
        severity_df = (
            pattern_df
            .groupBy("severity")
            .agg(
                count("*").alias("total_detected")
            )
            .orderBy(desc("total_detected"))
        )

        # Industry analysis
        industry_df = (
            analysis_df
            .groupBy("industry_category")
            .agg(
                count("*").alias("total_websites"),
                avg("credibility_score").alias(
                    "average_credibility_score"
                )
            )
            .orderBy(desc("total_websites"))
        )

        # Domain analysis
        domain_df = (
            analysis_df
            .groupBy("domain")
            .agg(
                count("*").alias("analysis_count"),
                avg("credibility_score").alias(
                    "average_credibility_score"
                )
            )
            .orderBy(desc("analysis_count"))
        )

        return {
            "pattern_frequency": [
                row.asDict()
                for row in pattern_frequency_df.collect()
            ],
            "severity_distribution": [
                row.asDict()
                for row in severity_df.collect()
            ],
            "industry_analysis": [
                row.asDict()
                for row in industry_df.collect()
            ],
            "domain_analysis": [
                row.asDict()
                for row in domain_df.collect()
            ]
        }

    finally:
        spark.stop()


if __name__ == "__main__":

    # darkpattern.db location
    db_path = os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        ),
        "darkpattern.db"
    )

    print("Database:", db_path)

    run_bda_analysis(db_path)