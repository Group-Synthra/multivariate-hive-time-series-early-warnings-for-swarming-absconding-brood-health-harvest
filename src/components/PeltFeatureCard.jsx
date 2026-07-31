import React from "react";

export default function PeltFeatureCard({

    title,
    icon,
    description,
    color

}){

    return(

        <div
            style={{
                background:"#1e293b",
                padding:20,
                borderRadius:15,
                borderTop:`5px solid ${color}`,
                transition:"0.3s",
                cursor:"pointer",
                height:"100%"
            }}
        >

            <div
                style={{
                    fontSize:40,
                    marginBottom:15
                }}
            >
                {icon}
            </div>

            <h3 style={{color}}>

                {title}

            </h3>

            <p
                style={{
                    color:"#cbd5e1",
                    lineHeight:1.6
                }}
            >
                {description}
            </p>

        </div>

    );

}