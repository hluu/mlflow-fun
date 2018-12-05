package org.andre.mlflow.examples

import java.io.{File,PrintWriter}
import org.mlflow.tracking.MlflowClient
import org.mlflow.tracking.creds.BasicMlflowHostCreds
import org.mlflow.api.proto.Service.RunStatus

object HelloWorld {
  def string2hex(str: String) = str.toList.map(_.toInt.toHexString+" ").mkString

  def main(args: Array[String]) {
    val trackingUri = args(0)
    println(s"Tracking URI: $trackingUri")

    // Create client
    val mlflowClient = 
      if (args.length > 1) {
        new MlflowClient(new BasicMlflowHostCreds(trackingUri,args(1)))
      } else {
        new MlflowClient(trackingUri)
      }

    // Create or get existing experiment
    val expName = "scala/HelloWorld"
    val expId = MLflowUtils.getOrCreateExperimentId(mlflowClient, expName)
    println("Experiment name: "+expName)
    println("Experiment ID: "+expId)

    // Create run
    val sourceName = (getClass().getSimpleName()+".scala").replace("$","")
    val runInfo = mlflowClient.createRun(expId, sourceName)
    val runId = runInfo.getRunUuid()

    // Log params and metrics
    mlflowClient.logParam(runId, "p1","hi")
    mlflowClient.logMetric(runId, "m1",0.123F)

    // Log artifact
    new PrintWriter("info.txt") { write("Run at: "+new java.util.Date()) ; close }
    mlflowClient.logArtifact(runId, new File("info.txt"))

    // Close run
    mlflowClient.setTerminated(runId, RunStatus.FINISHED, System.currentTimeMillis())
  }
}
