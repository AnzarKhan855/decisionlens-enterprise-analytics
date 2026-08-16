"use client";

import { useEffect, useState } from "react";

import api from "@/lib/api";


interface Anomaly {
  period: string;
  title: string;
  category: string;
  severity: string;
  type: string;
  actual_value: number;
  expected_value: number;
  z_score: number;
  pct_change: number;
  explanation: string;
  business_impact: string;
  possible_causes: string[];
  recommendation: string;
  confidence_score: number;
}


interface Summary {
  total_anomalies: number;
  critical: number;
  high: number;
  medium: number;
}



export default function AnomalyDetectionCard(){


    const [summary,setSummary] =
    useState<Summary | null>(null);


    const [anomalies,setAnomalies] =
    useState<Anomaly[]>([]);



    useEffect(()=>{


        async function fetchAnomalies(){

try{



                const response =
                await api.get(
                    "/analytics/anomalies"
                );



                setSummary(
                    response.data.summary
                );


                setAnomalies(
                    response.data.anomalies
                );


            }
            catch(error){


                console.error(
                    "Anomaly Error",
                    error
                );


            }


        }


        fetchAnomalies();


    },[]);





    if(!summary){

        return (

            <div
            className="
            bg-surface
            rounded-xl
            p-6
            border
            "
            >
                Loading anomaly analysis...
            </div>

        )

    }





    return (

        <div
        className="
        rounded-2xl
        border
        border-border-color
        bg-surface
        p-6
        shadow-sm
        premium-card
        "
        >


            <h3
            className="
            text-lg
            font-semibold
            text-text-primary
            "
            >
                Sales Anomaly Detection
            </h3>



            <p
            className="
            text-sm
            text-text-muted
            mt-1
            "
            >
                Statistical detection of unusual sales behaviour
            </p>




            <div
            className="
            grid
            grid-cols-4
            gap-3
            mt-6
            "
            >


                <div className="border rounded-lg p-3">

                    <p className="text-xs text-text-muted">
                        Total
                    </p>

                    <h4 className="text-xl font-bold">
                        {summary.total_anomalies}
                    </h4>

                </div>



                <div className="border rounded-lg p-3">

                    <p className="text-xs text-text-muted">
                        Critical
                    </p>

                    <h4 className="text-xl font-bold">
                        {summary.critical}
                    </h4>

                </div>




                <div className="border rounded-lg p-3">

                    <p className="text-xs text-text-muted">
                        High
                    </p>

                    <h4 className="text-xl font-bold">
                        {summary.high}
                    </h4>

                </div>



                <div className="border rounded-lg p-3">

                    <p className="text-xs text-text-muted">
                        Medium
                    </p>

                    <h4 className="text-xl font-bold">
                        {summary.medium}
                    </h4>

                </div>



            </div>





            {
                anomalies.map((item)=>(

                    <div
                    key={item.period}
                    className="
                    mt-5
                    border
                    rounded-xl
                    p-5
                    premium-card
                    "
                    >


                        <h4
                        className="
                        font-semibold
                        text-text-primary
                        "
                        >
                            {item.title}
                        </h4>



                        <p
                        className="
                        text-sm
                        text-text-secondary
                        mt-2
                        "
                        >
                            Period: {item.period}
                        </p>



                        <p
                        className="
                        text-sm
                        text-text-secondary
                        "
                        >
                            Actual: {item.actual_value.toLocaleString()} | Expected: {item.expected_value.toLocaleString()} (Z-Score: {item.z_score})
                        </p>



                        <p
                        className="
                        text-sm
                        text-text-secondary
                        "
                        >
                          Severity:
                          {" "}
                          <span className={`px-2 py-0.5 text-[11px] font-extrabold rounded-full border ${
                            item.severity === "Critical"
                              ? "bg-error-100 text-error-800 border-error-200"
                              : item.severity === "High"
                              ? "bg-warning-100 text-warning-800 border-warning-200"
                              : "bg-primary-100 text-primary-800 border-primary-200"
                          }`}>
                            {item.severity}
                          </span>
                        </p>



                        <p
                        className="
                        text-sm
                        text-text-muted
                        mt-2
                        italic
                        "
                        >
                            {item.explanation}
                        </p>

                        {item.recommendation && (
                          <p
                          className="
                          text-sm
                          text-primary-700
                          mt-2
                          font-medium
                          "
                          >
                            Recommendation: {item.recommendation}
                          </p>
                        )}

                    </div>


                ))
            }



        </div>


    );


}
